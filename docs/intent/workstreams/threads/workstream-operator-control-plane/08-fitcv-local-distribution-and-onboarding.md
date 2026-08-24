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
- [x] PyInstaller bundle, installer, checksum, and host-local packaged smoke
- [x] reinstall/uninstall preserve user data
- [ ] OPTIONAL clean-machine verification for public release

**Verification:**
- [x] bundle meets fixed size, idle-memory, health, and first-page budgets on documented local baseline
- [x] unsigned artifacts are explicitly labeled Technical Preview

**Exit Criteria:**
- personal-use packaged gate records host-local proof; clean-machine evidence remains a deferred public-release item

## Scope

- in scope:
  - Windows-first local packaging and launcher
  - browser onboarding and LLM setup
  - user-owned storage, backup, import, relocation, recovery, diagnostics, and shutdown
  - host-local packaged acceptance and fixed release budgets
  - truthful public setup and usage docs
- out of scope:
  - Electron or Tauri rewrite
  - automatic self-update
  - signed stable release before signing and clean-VM proof
  - external runtime repository or alternate transport
- deferred:
  - optional clean-machine acceptance and production code signing for public release

## Dependencies

- upstream:
  - `admin_control_plane_core`
  - `settings_system`
  - `trigger_run_management`
  - `run_lifecycle_controls`
- blockers:
  - none for personal-use packaged readiness
  - clean-machine evidence and code signing remain blockers only for public release readiness
- downstream handoff:
  - technical-preview checkpoint result pack and release acceptance follow-up

## Completion Criteria

### PERSONAL_PACKAGED_READY

1. clean packaging build and installer identity/hash are recorded
2. packaged launch, `/healthz`, fresh temporary FitCV data root, canonical onboarding,
   provider/model verification, and `/local/readiness` with `ready:true` pass
3. one real packaged pipeline Run reaches its intended terminal state
4. browser/API/artifact state reconciles, restart persistence passes, and singleton
   behavior passes
5. uninstall preserves user data and reinstall recovers prior state
6. logs and diagnostics contain no credentials

### OPTIONAL_CLEAN_MACHINE_VERIFIED

1. `PERSONAL_PACKAGED_READY` passes
2. clean-machine evidence is run separately and recorded as optional evidence
3. failure or omission does not block personal-use release

### PUBLIC_RELEASE_READY

1. `PERSONAL_PACKAGED_READY` passes
2. clean-machine acceptance passes
3. executable and installer are code-signed and signed hashes are published

Credential Manager ownership, loopback/Host/Origin/CSRF protections, secret
redaction, PID-scoped cleanup, and application/user-data separation remain
required in every classification. Sandbox relay proxy, temporary firewall
plumbing used only for VM testing, and pristine-machine Python/Git/Docker
absence checks are not routine personal-use requirements.
