---
layer: change
artifact_type: spec
status: proposed
template_id: detailed-specification
name: fitcv-local-distribution-and-onboarding
parent_thread: workstream-operator-control-plane.fitcv-local-distribution-and-onboarding
targets:
  - src/fitcv/config.py
  - src/fitcv/persistence.py
  - src/fitcv/runtime_routing.py
  - src/fitcv_cp/main.py
  - src/fitcv_cp/app.py
  - src/fitcv_cp/queue.py
  - src/fitcv_cp/backend_runtime.py
  - src/fitcv_cp/settings_schema.py
  - src/fitcv_cp/settings_store.py
  - src/fitcv_cp/local_app.py
  - src/fitcv_cp/local_storage.py
  - src/fitcv_cp/local_credentials.py
  - src/fitcv_cp/local_setup.py
  - src/fitcv_cp/local_routes.py
  - src/fitcv_cp/templates
  - config/runtime/control_plane.yaml
  - packaging/windows
  - docs/intent/project-charter.md
  - docs/fitcv-control-plane-setup.md
  - docs/features/trigger_run_management/feature.source.yaml
  - docs/setup.md
  - docs/configuration.md
  - docs/usage.md
  - README.md
  - tests/test_fitcv_cp
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

# FitCV Local Distribution And Onboarding Specification

## Goal

Define **FitCV Local**, a Windows-first local application distribution for
non-technical users. A user installs FitCV, launches it from the Start menu,
completes browser-based onboarding, and runs the existing FitCV control plane
without installing Docker, Python, Redis, Git, or a separate worker.

FitCV Local reuses the current FastAPI/Jinja browser UI and repo-owned pipeline.
It is not an Electron rewrite and not a second product. Distribution adds only
the local launcher, packaging, onboarding, user-owned configuration, safe data
relocation, and lifecycle controls needed to make the current product usable.

The shipped application has one runtime path. External `fitcv-langgraph`
packages, sibling checkouts, mounts, dynamic imports, feature flags, and
alternate transports are forbidden.

## Key Deliverables

### 1. Install-and-run local application

- one Windows installer contains FitCV, Python runtime, required packages,
  templates, static assets, and packaged default configuration
- Start menu launch starts one local application instance and opens the default
  browser to FitCV
- normal use requires no terminal, repository checkout, Docker, Redis, RQ
  worker, or manual environment file
- application binds to loopback only and chooses an available local port
- a second launch opens the existing instance instead of starting another
  server against the same data
- packaged mode protects against remote and cross-site browser requests; it
  does not claim isolation from another malicious process running as same OS user

### 2. Lightweight single-process runtime

- packaged mode runs web server and pipeline work in one application process
- packaged mode replaces daemon-per-enqueue inline threads with one process-owned
  `ThreadPoolExecutor(max_workers=1)`
- one pipeline or packaged background job executes at a time; additional run
  submissions reject with visible busy state instead of starting concurrently
- page refresh, browser close, and browser reopen do not cancel an active run
- graceful shutdown drains no work because shutdown is rejected while executor
  has queued or running work
- unexpected process loss leaves interrupted runs for existing orphan recovery
  to terminalize on next startup
- Docker and Redis/RQ remain developer or server deployment options only

### 3. User-owned data and configuration

- first launch activates `%LOCALAPPDATA%\FitCV\data` as safe default
- onboarding allows user to keep or change data location before first pipeline
  run; later changes are cold restart operations
- `%APPDATA%\FitCV\bootstrap.json` stores only selected data-root pointer and
  minimal bootstrap metadata
- chosen data folder owns SQLite database, candidate profile, run artifacts,
  exports, logs, backups, and non-secret user configuration
- packaged defaults remain read-only application resources
- packaged `config/runtime/control_plane.yaml` remains canonical
- user data stores one versioned, narrow non-secret overlay limited to provider
  definitions and `model_routing.parts`; full packaged config is never copied
- effective control-plane config resolves through one merge owner: packaged
  defaults, then local overlay, then explicit supported per-run overrides
- all packaged mutable writes resolve under data root; installation directory is
  verified read-only during normal operation

### 4. First-run onboarding

Onboarding is a resumable wizard:

1. **Welcome and local-data notice**
   - explain local execution and which external LLM provider receives data
2. **Data location**
   - show active default, allow native folder selection before first run, and
     reject UNC, network, and removable destinations in first release
3. **Candidate profile**
   - create from template, import supported YAML/JSON, or defer with a visible
     run-blocking status
4. **LLM provider**
   - choose provider type, enter endpoint and credential when required, test
     connection
5. **Models**
   - choose one default model and optional advanced per-task overrides
6. **Review and finish**
   - show data location, provider, model routes, and readiness checks

Onboarding completion means application shell is configured. Model-backed run
creation remains blocked until candidate profile and required LLM route checks
pass.

### 5. LLM provider and model setup

Provider contract supports:

- **OpenAI**: fixed official API-root base URL, `auth_mode: required`, and
  packaged wire API default
- **OpenAI-compatible**: user display name, API-root base URL,
  `auth_mode: required | optional | none`, and explicit wire API selection

Provider invariants:

- `base_url` is API root such as `https://provider.example/v1`, never an
  operation endpoint such as `/chat/completions`
- transport appends endpoint path from `wire_api`
- model discovery uses `{base_url}/models`
- readiness, connection test, discovery, and pipeline execution use same
  provider validator and normalized route
- no automatic wire-API detection is required in first release

Model setup supports:

- bounded connection test with actionable errors
- `/models` discovery when supported
- manual model ID entry fallback
- one default model for all LLM tasks
- advanced overrides for enrichment extraction, ranking AI score, structured
  CV generation, and synonym triage recommendation
- visible effective provider and model summary per task

Credentials live in Windows Credential Manager. They must not be written to
YAML, JSON, SQLite, logs, backups, exports, HTML, diagnostics, or run artifacts.
API responses expose only credential state, never credential values.

### 6. Database location, backup, and restore

UI exposes a **Data & Backup** page showing:

- resolved data folder and SQLite database path
- database size and last backup time
- **Change Location**
- **Download Backup**
- **Import Backup**

Location selection uses native Windows folder picker opened by local backend.
Browser file APIs must not infer or expose arbitrary local paths.

Backup, import, and relocation are rejected while executor has queued or running
work. Backup uses SQLite native backup API; raw copying active DB/WAL files is
forbidden.

Backup archive contract `fitcv-backup.v1` contains:

- manifest version, application version, data-layout version, DB schema version,
  creation time, included paths, sizes, and SHA-256 checksums
- SQLite backup snapshot
- candidate profile
- narrow non-secret routing overlay
- selected completed-run artifacts

Archive excludes credentials, authorization headers, logs, prior backups,
exports, temporary files, runtime metadata, WAL/SHM files, and incomplete-run
artifacts.

Import and relocation are cold launcher operations:

1. validate request and destination while application is idle
2. write pending operation and shut application down
3. stage operation before any DB is opened on restart
4. validate archive/path, checksums, schema compatibility, SQLite integrity, and
   required files
5. atomically update bootstrap pointer only after validation
6. restart application and verify storage opens
7. restore previous pointer and retained source if restart validation fails

Source deletion is never automatic. First release accepts local fixed-disk
absolute directories only and rejects UNC, network, and removable roots.
Destination must have free space of at least twice current data-root size plus
512 MiB. Backup upload is capped at 4 GiB, extracted content at 8 GiB, and one
archive member at 2 GiB.

### 7. Local web security and shutdown

Packaged mode uses one global web-security contract, not route-local guards:

- bind preselected random port on `127.0.0.1`
- validate expected `Host` for every request
- validate same-origin `Origin`/`Referer` for every unsafe method
- require one per-process CSRF token for every unsafe existing and new route
- inject CSRF token through shared template context and form helper
- expose no login/session system in first release

A second launch opens existing URL and needs no one-time authentication token.

Application menu includes **Shutdown** only in local packaged mode.

- action is `POST`, CSRF-protected, and requires confirmation
- endpoint is unavailable outside loopback-bound packaged mode
- shutdown is rejected while executor has queued or running work
- accepted shutdown stops new work, flushes settings and logs, closes database
  handles, stops server, and exits launcher
- browser receives final “FitCV has stopped” page before connection closes
- browser refresh cannot restart application

### 8. Distribution and release artifacts

Windows release output contains versioned installer, unpacked smoke-test bundle,
SHA-256 checksums, release notes, supported migration range, and uninstall entry
that preserves user data by default.

Packaging uses a directory-based Python bundle rather than one compressed
executable. This avoids repeated extraction, reduces startup delay, and makes
antivirus behavior more predictable. Installer creates Start menu entry and
optional desktop shortcut.

Automatic self-update is not in first release. UI may show current version,
change log, and manually initiated update link. Signed background updates wait
until signing and rollback behavior are proven.

Release budgets use Windows 11, 4 logical CPU cores, 8 GiB RAM, and SSD baseline:

- installed application size: at most 600 MiB
- idle resident memory after runs page loads: at most 250 MiB
- cold launch to healthy local server: at most 8 seconds
- cold launch to first rendered page: at most 10 seconds

Changing budgets requires explicit spec revision before release evidence; Task 1
cannot redefine them after implementation begins.

Public release requires signed installer and executable. Unsigned output may be
published only as explicitly labeled technical preview.

### 9. Support diagnostics

**Download Diagnostics** contains application/build version, OS/runtime metadata,
redacted data path, database schema and integrity state, provider type, base
host, wire API, model IDs, recent sanitized logs, and readiness checks.

Diagnostics exclude API keys, authorization headers, candidate-profile
contents, prompts, CV contents, job descriptions, and raw database rows.

## Task/Wave Breakdown

### Wave 1: Distribution boundary

**Purpose:**
- establish packaged-local mode without changing server/developer behavior

**Steps:**
- [ ] define packaged startup and single-instance contract
- [ ] package current web UI and runtime into Windows directory bundle
- [ ] add one serialized process executor and loopback binding in packaged mode
- [ ] add one global packaged-mode Host/Origin/CSRF guard covering all unsafe routes
- [ ] remove end-user dependency on Docker, Redis, RQ worker, `.env`, and repo paths

**Verification:**
- [ ] clean Windows user can install, launch, and reach onboarding offline
- [ ] existing Docker/server entrypoints retain current behavior

**Exit Criteria:**
- installer launch reaches one local FitCV instance without developer tooling

### Wave 2: User data ownership

**Purpose:**
- move mutable state out of application installation directory

**Steps:**
- [ ] add atomic bootstrap pointer file
- [ ] add narrow provider/model overlay merged into packaged config through one owner
- [ ] create and validate selected data root
- [ ] implement native SQLite backup and cold import/location migration

**Verification:**
- [ ] application remains functional after reinstall with preserved data root
- [ ] failed migration or import preserves original usable data

**Exit Criteria:**
- every mutable non-secret user artifact has one documented owner

### Wave 3: Onboarding and LLM readiness

**Purpose:**
- replace manual config editing with guided setup

**Steps:**
- [ ] add resumable onboarding state
- [ ] add candidate-profile create/import flow
- [ ] add provider, credential, connection-test, and model-routing flow
- [ ] enforce explicit provider API-root, auth-mode, and wire-API schema
- [ ] add readiness summary and run-trigger blocking reasons

**Verification:**
- [ ] first-run user can configure OpenAI and OpenAI-compatible providers
- [ ] secrets never appear in files, responses, logs, or backups
- [ ] invalid provider setup produces actionable feedback

**Exit Criteria:**
- user finishes setup without editing files or environment variables

### Wave 4: Lifecycle and support controls

**Purpose:**
- complete local application operation from browser UI

**Steps:**
- [ ] add guarded web-UI shutdown
- [ ] add version, change-log, and diagnostics surfaces
- [ ] protect backup, shutdown, import, and relocation during queued/running work
- [ ] add recovery messaging for startup and storage failures

**Verification:**
- [ ] shutdown exits all FitCV Local processes when idle
- [ ] unsafe lifecycle actions reject without data loss

**Exit Criteria:**
- start, operate, diagnose, back up, restore, relocate, and stop need no terminal

### Wave 5: Release proof

**Purpose:**
- prove distributable artifact on clean machine profile

**Steps:**
- [ ] build versioned installer and checksum output
- [ ] run clean-install, upgrade, uninstall, and preserve-data checks
- [ ] run onboarding and one representative pipeline smoke run
- [ ] update public setup and usage docs for FitCV Local
- [ ] prove fixed size/start/memory budgets and public code-signing disposition

**Verification:**
- [ ] release checklist records installer hash and clean-machine evidence
- [ ] docs separate FitCV Local from developer Docker/server setup

**Exit Criteria:**
- release artifact satisfies completion criteria

## Design Decisions

### Decision: Keep browser UI; add local launcher

- context: current FastAPI/Jinja control plane already owns operator workflows
- choice: package existing UI and open it in user's default browser
- alternatives considered:
  - Electron rewrite
  - Tauri rewrite
  - native Windows UI rewrite
- impact:
  - smallest product and maintenance change
  - browser owns presentation; launcher owns process and native-dialog lifecycle

### Decision: Windows-first distribution

- context: current local scripts and target environment are Windows-heavy
- choice: prove one Windows installer before macOS or Linux packages
- alternatives considered:
  - simultaneous three-platform release
  - Docker-only desktop wrapper
- impact:
  - folder picker, credential storage, installer, and smoke evidence stay concrete
  - no speculative cross-platform framework is required

### Decision: Single-process serialized execution

- context: Redis and separate worker create most startup complexity
- choice: packaged mode uses one process-owned `ThreadPoolExecutor(max_workers=1)`
  with explicit busy rejection and existing orphan recovery after unexpected exit
- alternatives considered:
  - bundle Redis and RQ invisibly
  - ship multiple managed child processes
  - replace RQ with new embedded queue dependency
- impact:
  - lower memory, fewer failure modes, simpler shutdown
  - daemon-per-enqueue inline threads are removed from packaged semantics
  - multi-user and high-throughput execution remain server-mode concerns

### Decision: User chooses data folder, not raw database internals

- context: users need ownership and portability without editing SQLite filenames
- choice: activate safe default on first launch, expose data-root selection before
  first run, and perform later moves only as cold launcher operations
- alternatives considered:
  - raw SQLite file path input
  - fixed hidden application-data path
- impact:
  - database, artifacts, profile, logs, and backups move as one unit
  - migration can be validated and rolled back atomically

### Decision: Use narrow local config overlay

- context: copying packaged control-plane config would fork defaults across upgrades
- choice: keep packaged config canonical and persist only provider/model overrides
- alternatives considered:
  - copy full packaged YAML into user data
  - persist secrets and routing together in SQLite
- impact:
  - upgrades inherit new packaged defaults automatically
  - one merge owner defines effective runtime routing

### Decision: Use one global packaged web guard

- context: existing control-plane POST routes already mutate runs and settings
- choice: enforce loopback Host/Origin checks and CSRF on every unsafe route in
  packaged mode without adding login/session state
- alternatives considered:
  - guard only new local routes
  - one-time browser login token plus session cookie
- impact:
  - existing and new mutations share one security contract
  - second launch opens existing URL without token-transfer protocol

### Decision: Use cold data mutation

- context: SQLite connections are opened across control-plane and pipeline modules
- choice: backup through SQLite native API; perform restore and relocation before
  DB initialization during launcher restart
- alternatives considered:
  - close every connection and hot-swap storage in running process
  - raw copy live SQLite/WAL files
- impact:
  - no custom connection registry or live global-path rebinding is required
  - data operations are slower but uniformly recoverable

### Decision: Fixed bootstrap pointer outside data root

- context: application must find selected or moved data root before opening DB
- choice: store minimal atomic JSON pointer under `%APPDATA%\FitCV`
- alternatives considered:
  - Windows Registry
  - environment variable
  - pointer file inside installation directory
- impact:
  - stdlib JSON and atomic file replacement are sufficient
  - reinstall and upgrades do not overwrite data ownership

### Decision: OS credential store owns API keys

- context: user-owned backup must not make secrets portable plaintext
- choice: Windows Credential Manager stores provider credentials; config stores
  only credential reference and state
- alternatives considered:
  - `.env` file
  - encrypted SQLite value with application-owned key
  - plaintext YAML
- impact:
  - backups remain secret-free
  - credential replacement and deletion need explicit UI actions

### Decision: Default model plus advanced task overrides

- context: most users need one model; advanced users need route control
- choice: onboarding asks for one default and hides per-task routes under Advanced
- alternatives considered:
  - require four model selections
  - expose one hard-coded model
- impact:
  - simple path stays short while internal routing remains representable

### Decision: Use explicit provider transport schema

- context: optional credentials and `/models` discovery require unambiguous route shape
- choice: provider config owns API-root `base_url`, `auth_mode`, and `wire_api`
- alternatives considered:
  - infer authentication from missing key
  - accept operation endpoint URLs and rewrite them heuristically
- impact:
  - readiness, discovery, test request, and runtime transport resolve identically

### Decision: No automatic updates in first release

- context: safe self-update requires signing, rollback, and locked-file handling
- choice: ship versioned installers and manual update notification first
- alternatives considered:
  - unsigned background updater
  - custom patch downloader
- impact:
  - distribution ships without a second high-risk lifecycle system

## Invariants

- FitCV Local starts without Docker, Redis service, separate worker, Python, Git, or terminal commands.
- Existing pipeline stage order and stage-owned result semantics do not change.
- Packaged mode and server/developer mode share pipeline business code.
- No external `fitcv-langgraph` dependency, mount, import, dynamic loader, feature flag, or transport path exists.
- Application binds to `127.0.0.1` or `::1` only in packaged mode.
- Every unsafe packaged-mode route, existing or new, shares Host/Origin/CSRF enforcement.
- Packaged mode has no browser login/session contract; second launch opens existing URL.
- One process-owned executor serializes packaged pipeline and background jobs.
- One user data root owns all mutable non-secret application data.
- Installation directory remains read-only during normal operation.
- Packaged control-plane config remains canonical; local file is a narrow validated overlay only.
- API keys never enter user config, SQLite, backups, exports, logs, diagnostics, HTML, or run artifacts.
- Backup, relocation, and import cannot run during queued or active packaged work.
- Backup uses SQLite native backup API; restore and relocation run before DB opens.
- Failed relocation, import, upgrade, or migration leaves recoverable prior data.
- Shutdown is POST-only, CSRF-protected, packaged-mode-only, loopback-only, and rejected during active work.
- Browser close does not terminate application or active run.
- Uninstall preserves user data unless user explicitly requests deletion.
- Provider and model UI writes through same internal runtime-routing owner used by pipeline execution.
- Provider base URL is API root and auth requirement is explicit, never inferred.
- Per-run effective settings remain captured in `settings-used.json`.
- Packaged defaults are versioned with application; user overrides survive upgrades.
- Incomplete onboarding is visible and blocks only actions requiring missing configuration.
- No plugin system, provider SDK framework, desktop UI rewrite, or bundled infrastructure supervisor is added.
- Public installer/executable are signed; unsigned artifacts are labeled technical preview.

## Validation Plan

- proof target: clean install needs no developer tooling
  - method: install on Windows profile without Python, Git, Docker, or Redis
  - evidence: Start menu launch opens onboarding and health check passes

- proof target: application stays lightweight
  - method: record installed size, cold-start time, idle memory, and first-page time
  - evidence: installed <= 600 MiB, idle RSS <= 250 MiB, healthy <= 8 seconds,
    first page <= 10 seconds on documented Windows 11 baseline

- proof target: packaged mode uses one runtime path
  - method: process inspection plus source/config search
  - evidence: one FitCV process family; no Redis/RQ worker child; no `fitcv-langgraph` references

- proof target: data ownership survives reinstall and upgrade
  - method: create runs, install newer build, reopen same data root
  - evidence: runs, settings, profile, and artifacts remain available

- proof target: location migration is loss-safe
  - method: cold launcher success case plus injected staging, integrity, pointer,
    restart-validation, and rollback failures
  - evidence: destination activates only after validation; source remains recoverable

- proof target: backup and restore are portable and secret-free
  - method: inspect `fitcv-backup.v1`, restore before DB open, scan archive contents
  - evidence: checksums and schema validate, data restores, excluded paths stay
    absent, and no credential value exists in archive

- proof target: LLM onboarding supports required providers
  - method: test OpenAI, authenticated OpenAI-compatible, and unauthenticated local compatible endpoint
  - evidence: connection test, discovery/manual fallback, saved routing, and representative request succeed

- proof target: credential boundary holds
  - method: secret-canary scan across files, DB, logs, backup, diagnostics, API responses, and HTML
  - evidence: canary exists only in credential-store lookup path

- proof target: active-run lifecycle protection works
  - method: attempt backup, shutdown, import, and relocation during queued/running job
  - evidence: actions reject clearly; run and database remain healthy

- proof target: shutdown exits cleanly
  - method: idle shutdown followed by process and port inspection
  - evidence: browser receives stopped state; port closes; no FitCV Local process remains

- proof target: server/developer mode does not regress
  - method: focused control-plane, queue, settings, and Docker smoke checks
  - evidence: current supported server paths retain existing behavior

- proof target: public docs match distribution behavior
  - method: fresh-user walkthrough using README, setup, control-plane setup,
    configuration, usage, architecture, and project charter
  - evidence: no hidden terminal, `.env`, Redis, worker, or repo prerequisite appears in FitCV Local path

## Completion Criteria

This specification is complete when:

1. product owner approves Windows-first browser-based FitCV Local shape
2. packaged mode installs and starts without developer prerequisites
3. one in-process run path replaces Redis/RQ requirements for packaged users
4. onboarding covers data location, candidate profile, LLM provider, credential test, and model routing
5. user data, user config, packaged defaults, and secrets have distinct documented owners
6. SQLite-native backup and cold relocation/restore preserve recoverability under failure
7. web-UI shutdown is guarded and exits application cleanly
8. installer upgrade and uninstall preserve user data by default
9. no external `fitcv-langgraph` path or reference remains
10. global packaged-route security, serialized executor, provider schema, fixed
    performance budgets, code signing, clean-machine smoke, and documentation checks pass
11. downstream implementation plan is completed or explicitly dropped
12. every child item is `completed` or `dropped`

Canonical source-of-truth:

<LINK>
- `docs/intent/workstreams/threads/workstream-operator-control-plane/08-fitcv-local-distribution-and-onboarding.md`
- `docs/features/admin_control_plane_core/feature.source.yaml`
- `docs/features/settings_system/feature.source.yaml`
- `docs/features/trigger_run_management/feature.source.yaml`
- `docs/features/run_lifecycle_controls/feature.source.yaml`
- `docs/intent/project-charter.md`
- `docs/fitcv-control-plane-setup.md`
- `src/fitcv_cp/main.py`
- `src/fitcv_cp/app.py`
- `src/fitcv_cp/queue.py`
- `src/fitcv/runtime_routing.py`
- `config/runtime/control_plane.yaml`
- `docs/operating_system/lifecycle/doc-system-lifecycle.md`
- `scripts/validate_planning_lifecycle.py`
</LINK>
