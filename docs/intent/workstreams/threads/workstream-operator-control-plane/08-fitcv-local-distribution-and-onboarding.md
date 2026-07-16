---
thread_id: workstream-operator-control-plane.fitcv-local-distribution-and-onboarding
status: proposed
---

# fitcv-local-distribution-and-onboarding

## Goal

Ship FitCV as a local, user-friendly application that starts without Docker,
Redis, a separate worker, repository checkout, or terminal setup while keeping
the existing browser control plane as the primary UI.

## Why Now

Current installation and startup requirements exclude non-technical users.
The external `fitcv-langgraph` runtime path has been removed, so distribution
can now target one repo-owned runtime and one onboarding contract.

## Dependencies

- `admin_control_plane_core`
- `settings_system`
- `trigger_run_management`
- `run_lifecycle_controls`

## Shared Surfaces

- application packaging and launcher
- first-run onboarding
- user-owned data and configuration location
- LLM provider, credential, and model routing setup
- local process lifecycle and web-UI shutdown
- backup, restore, and data-location migration

## Notes

- Windows is the first distribution target.
- Existing Docker and queue mode remain developer/server deployment options,
  not end-user prerequisites.
- No external `fitcv-langgraph` dependency, mount, import, or transport path may
  return through this thread.
- The next artifact is the detailed distribution specification, followed by an
  implementation plan after approval.
