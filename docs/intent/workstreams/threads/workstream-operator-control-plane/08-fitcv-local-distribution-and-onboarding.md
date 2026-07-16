---
thread_id: workstream-operator-control-plane.fitcv-local-distribution-and-onboarding
status: active
---

# fitcv-local-distribution-and-onboarding

## Goal

Ship FitCV as a local, user-friendly Windows application that starts without
Docker, Redis, separate worker, repository checkout, or terminal setup while
reusing existing browser control plane and internal runtime.

## Key Deliverables

### Installable local runtime

Provide PyInstaller `onedir` bundle and per-user Inno Setup installer with one
loopback process, second-instance reuse, serialized work, technical-preview
labeling, checksums, and preserved user data.

### User-owned onboarding and operations

Provide resumable browser onboarding, selected data root, OS credential storage,
narrow provider/model overlay, readiness gating, backup/import/relocation,
redacted diagnostics, recovery, and web-UI shutdown.

## Task/Wave Breakdown

### Wave 1: Runtime and onboarding

**Purpose:**
- remove end-user infrastructure prerequisites without changing server mode

**Checks:**
- [x] single-instance loopback launcher and serialized executor
- [x] user-owned storage bootstrap and local credential boundary
- [x] provider/model onboarding and readiness gate
- [x] packaged Host, Origin/Referer, and CSRF enforcement

**Verification:**
- [x] focused source tests cover launcher, storage, setup, routes, and credentials

**Exit Criteria:**
- source packaged mode reaches onboarding without Redis or RQ worker

### Wave 2: Data lifecycle and distribution

**Purpose:**
- produce recoverable local data lifecycle and installable technical preview

**Steps:**
- [x] backup, import, relocation, diagnostics, recovery, and shutdown
- [x] PyInstaller bundle, installer, checksum, and isolated local smoke
- [x] reinstall/uninstall preserve user data
- [ ] clean Windows VM verifies no Python, Git, Docker, Redis, or network prerequisite

**Verification:**
- [x] bundle meets fixed size, idle-memory, health, and first-page budgets on documented local baseline
- [x] unsigned artifacts are explicitly labeled Technical Preview

**Exit Criteria:**
- checkpoint result pack records proof and clean-VM limitation

## Scope

- in scope:
  - Windows-first local packaging and launcher
  - browser onboarding and LLM setup
  - user-owned storage, backup, import, relocation, recovery, diagnostics, and shutdown
  - packaged security and fixed release budgets
  - truthful public setup and usage docs
- out of scope:
  - Electron or Tauri rewrite
  - automatic self-update
  - signed stable release before signing and clean-VM proof
  - external runtime repository or alternate transport
- deferred:
  - clean Windows VM acceptance and production code signing

## Dependencies

- upstream:
  - `admin_control_plane_core`
  - `settings_system`
  - `trigger_run_management`
  - `run_lifecycle_controls`
- blockers:
  - clean Windows VM and code-signing infrastructure for stable release
- downstream handoff:
  - technical-preview checkpoint result pack and release acceptance follow-up

## Completion Criteria

1. installer and unpacked bundle are reproducible and checksum-backed
2. onboarding, data ownership, credentials, backup, diagnostics, and shutdown are documented and tested
3. server/Docker/Redis/RQ behavior remains available outside packaged mode
4. checkpoint pack records local proof and unresolved clean-VM/signing gates
