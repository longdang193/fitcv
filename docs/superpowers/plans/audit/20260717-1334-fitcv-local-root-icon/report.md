# FitCV Local Root And Application Icon Audit

## Metadata

- Audit ID: `20260717-1334-fitcv-local-root-icon`
- Status: `resolved`
- Severity: `medium`
- Owner: `Codex`
- Created At: `2026-07-17T13:34:02+02:00`
- Updated At: `2026-07-17T15:24:48+02:00`
- Related Thread/Plan: `docs/superpowers/plans/2026-07-17-10-17-fitcv-local-controller-ssot-and-safe-prompt-customization-plan.md`

## Scope

- Environment: Windows 10, Python 3.13.5, PyInstaller 6.21.0, Inno Setup 6.7.3
- Commit/Branch: `d210f548` / `codex/phase-6-inverse-optimization`
- Affected Surface: packaged launcher, local root route, executable and installer icon resources, native Windows tray lifecycle

## Findings

### Finding F1: Completed onboarding exposes missing root route

- Classification: `regression`
- Impact: launching the packaged executable opens an unusable JSON 404 page for existing users.
- Expected Behavior: loopback root redirects to onboarding before setup and run dashboard after setup.
- Actual Behavior: middleware redirects incomplete setup, but completed setup falls through to an undefined `/` route.

### Finding F2: Windows package has no branded icon

- Classification: `spec-mismatch`
- Impact: executable, installer, and inherited shortcuts use generic Windows icons.
- Expected Behavior: packaged executable and installer use one FitCV icon.
- Actual Behavior: PyInstaller `EXE` and Inno Setup omit icon configuration.

### Finding F3: Packaged tray registration disappears immediately

- Classification: `regression`
- Impact: FitCV keeps running, but users have no visible Open or Shutdown tray control.
- Expected Behavior: packaged startup registers one FitCV tray icon until shutdown.
- Actual Behavior: `Shell_NotifyIconW(NIM_ADD)` rejects the tray registration in the full frozen executable.

## Evidence

- User root failure: `evidence/images/root-not-found.png`
- User notification-area inspection: `evidence/images/no-tray-icon.png`
- Initial behavior record: `evidence/results/initial-runtime.txt`
- Verification record: `evidence/results/verification.txt`
- Packaged tray verification: owner window, shell icon rectangle, Open command, and Shutdown command in `evidence/results/verification.txt`

## Reproduction

- Preconditions and deterministic commands: `repro/repro_steps.md`.

## Root Cause And Boundary

- Failure boundary: `src/fitcv_cp/app.py` local-mode route assembly, Windows packaging configuration, and `src/fitcv_cp/windows_tray.py` shell registration.
- Root cause summary: local middleware handled incomplete onboarding but no root route handled completed onboarding; package definitions never referenced an icon asset. Tray registration also omitted its owner `hWnd`, then reused a persistent GUID across probe and product executables. The shell rejected that stale/colliding GUID identity while GUID-free `hWnd + uID` registration succeeded.

## Fix And Verification

- Fix summary: add one local root redirect, add one `fitcv.ico`, reuse it for PyInstaller and Inno Setup, assign the tray owner window before registration, and use transient `hWnd + uID` tray identity instead of persistent GUID state.
- Verification commands:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_fitcv_cp/test_local_routes.py tests/test_fitcv_cp/test_local_app.py tests/test_fitcv_local_packaging.py -q
.\.venv\Scripts\python.exe -m pytest tests/test_fitcv_cp/test_windows_tray.py tests/test_fitcv_cp/test_local_app.py tests/test_fitcv_local_packaging.py -q
powershell -ExecutionPolicy Bypass -File scripts/build_fitcv_local.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\smoke_fitcv_local.ps1 -BundlePath .\dist\fitcv-local
```

- Verification evidence: `evidence/results/verification.txt`

## Risk And Disposition

- Residual risk: Windows controls final tray placement; icon can appear directly on taskbar or inside notification overflow according to user preferences.
- Disposition decision: `resolved`.
- Follow-ups: retain web UI shutdown as fallback and keep packaged shell-registration evidence in release verification.

## Artifact Index

- Manifest: `manifest.yaml`
- Evidence root: `evidence/`
- Repro root: `repro/`

## Completion Checklist

- [x] qualifying trigger documented
- [x] evidence bundle linked and hashed
- [x] deterministic repro steps included
- [x] expected vs actual included
- [x] verification evidence attached
- [x] final status recorded
