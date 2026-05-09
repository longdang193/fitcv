---
doc_id: usage
doc_type: operator-guide
explains:
  features:
    - inspection_debugging
    - settings_system
    - trigger_run_management
  stages:
    - cv_analysis
    - cv_generation
    - ranking
---

# Usage

FitCV usage splits into operator usage (UI/API) and engineering usage (runtime/tests/docs sync).

## Operator Flow

Entry point: `/admin/runs`

1. trigger a run (path/upload/paste)
2. choose run mode (`Run All` or `Stage by Stage`)
3. monitor events, stage progress, and lifecycle state
4. inspect run detail tabs and stage artifacts
5. export evidence (`export.json`, `cv-debug.json`, `settings-used.json`, stage artifacts, artifacts zip)

## Lifecycle Actions

- stop/cancel
- continue from checkpoints
- archive/unarchive
- reconciliation and repair actions when needed

## Settings Workflow

Use `/admin/settings` to tune future-run defaults.

Operator truth model:

1. adjust shared defaults on `/admin/settings`
2. optionally apply trigger-time per-run overrides when starting a run
3. verify historical run truth from run-level `settings-used.json`

Important:

- editing settings does not rewrite past runs
- per-run overrides do not change shared saved defaults
- metadata-only rows in Settings are informational (runtime-owned), not editable controls
- historical/debug truth for a run always comes from that run's `settings-used.json`, not from whatever defaults are currently visible on `/admin/settings`

Editable vs fixed controls:

- editable controls: schema-backed fields that are persisted as future defaults when saved
- fixed controls: runtime-owned, metadata-only fields shown for transparency and provenance

## Engineering Workflow

1. run app/worker in sqlite or bigquery mode
2. reproduce/verify via live run
3. run focused tests
4. run contract/validator checks before merge

## Key Surfaces

- `GET /healthz`
- `POST /runs`
- `GET /runs/{run_id}`
- `/admin/runs`
- `/admin/runs/{run_id}`
- `/admin/settings`

## Related Docs

- [setup.md](setup.md)
- [pipeline.md](pipeline.md)
- [architecture.md](architecture.md)
