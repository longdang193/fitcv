# Audit Report With Evidence

## Metadata

- Audit ID: `20260716-fitcv-local-windowed-runtime`
- Status: `resolved`
- Severity: `high`
- Owner: `Codex`
- Created At: `2026-07-16T23:55:00+02:00`
- Updated At: `2026-07-16T23:59:30+02:00`
- Related Thread/Plan: `docs/superpowers/plans/2026-07-16-22-40-fitcv-local-distribution-and-onboarding-plan.md`

## Scope

- Environment: Windows 11, Python 3.13, PyInstaller `onedir`, windowed executable, Uvicorn loopback server.
- Commit/Branch: `ef610fc63eb3b1cbe3e42553dc5e2fe11c95d2c7` on `codex/phase-6-inverse-optimization`, plus uncommitted Tasks 6-9 work.
- Affected Surface: FitCV Local packaged startup, configuration loading, and HTTP readiness.

## Findings

### Finding FLR-1: Packaged config default missing

- Classification: `environment`
- Impact: Every packaged launch stopped before HTTP startup.
- Expected Behavior: Bundle starts with safe packaged defaults, then switches candidate data to user-owned storage.
- Actual Behavior: `fitcv.settings_schema` imported `load_config()` and raised `FileNotFoundError: Config file not found: .env.yaml`.

### Finding FLR-2: Windowed standard streams stalled Uvicorn

- Classification: `environment`
- Impact: Process listened on loopback, but health requests did not complete.
- Expected Behavior: Windowed executable serves `/healthz` without console streams.
- Actual Behavior: PyInstaller windowed mode set `sys.stdout` and `sys.stderr` to `None`; Uvicorn stalled while handling requests.

## Evidence

- Failure trace: `evidence/results/missing-packaged-config.txt`
  - Capture timestamp: `2026-07-16T23:55:00+02:00`
  - Producer: `tmp/fitcv-local-debug/stderr.txt`
  - Checksum: `manifest.yaml`
- Fix and artifact evidence: `evidence/results/fix-artifacts.txt`
  - Capture timestamp: `2026-07-16T23:55:00+02:00`
  - Producer: `Get-FileHash`, bundle-size inspection, and source inspection
  - Checksum: `manifest.yaml`
- Fresh packaged smoke: `evidence/results/fresh-smoke.txt`
  - Capture timestamp: `2026-07-16T23:58:00+02:00`
  - Producer: isolated `scripts/smoke_fitcv_local.ps1` execution
  - Checksum: `manifest.yaml`
- Final installer lifecycle: `evidence/results/final-installer.txt`
  - Capture timestamp: `2026-07-16T23:59:30+02:00`
  - Producer: isolated silent install, installed-bundle smoke, reinstall, and uninstall
  - Checksum: `manifest.yaml`

## Reproduction

- Preconditions:
  - Build a windowed PyInstaller `onedir` executable.
  - Omit packaged `.env.yaml` for FLR-1.
  - Restore `.env.yaml` but omit runtime stdio hook for FLR-2.
- Steps and exact commands: `repro/repro_steps.md`
- Determinism notes: Both failures reproduced with isolated `%APPDATA%` and `%LOCALAPPDATA%`; no external service or network dependency was involved.

## Root Cause And Boundary

- Failure boundary: Packaged-only bootstrap before and during Uvicorn request handling.
- Root cause summary:
  - Existing import-time settings contract requires `.env.yaml`; source checkout supplied it, packaged bundle did not.
  - Windowed PyInstaller intentionally removes console streams; Uvicorn expected writable stream objects.
- Boundary decision: Do not modify CRITICAL shared `load_config`; provide packaged resources and a packaged runtime hook instead.

## Fix And Verification

- Fix summary:
  - Bundle `packaging/windows/.env.yaml` as safe startup defaults.
  - Add `packaging/windows/pyi_rth_stdio.py` to redirect missing standard streams to `os.devnull`.
  - Keep user-owned candidate profile and routing overlay outside install directory.
- Verification commands:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\build_fitcv_local.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\smoke_fitcv_local.ps1 -BundlePath .\dist\fitcv-local
.\.venv\Scripts\python.exe scripts\audit_check.py docs\superpowers\plans\audit\20260716-fitcv-local-windowed-runtime
```

- Verification evidence links:
  - `evidence/results/fix-artifacts.txt`
  - `evidence/results/fresh-smoke.txt`
  - `evidence/results/final-installer.txt`

## Risk And Disposition

- Residual risk: Clean Windows VM proof without Python, Git, Docker, Redis, or network remains outstanding. Silent uninstall removed installed files but left empty custom install directory.
- Disposition decision: `resolved`
- Follow-ups: Run clean-VM release acceptance before stable signing or non-preview release.

## Artifact Index

- Manifest: `manifest.yaml`
- Evidence root: `evidence/`
- Repro root: `repro/`

## Completion Checklist

- [x] qualifying trigger documented
- [x] evidence bundle linked and hashed
- [x] deterministic repro steps included
- [x] expected vs actual included
- [x] fresh verification evidence attached
- [x] final status recorded
