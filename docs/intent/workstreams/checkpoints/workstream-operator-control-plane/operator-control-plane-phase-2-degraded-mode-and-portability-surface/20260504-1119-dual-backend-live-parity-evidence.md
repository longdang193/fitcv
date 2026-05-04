# Checkpoint Result Pack

## Metadata

- Checkpoint ID: `workstream-operator-control-plane.operator-control-plane-phase-2-degraded-mode-and-portability-surface.20260504-1119`
- Workstream ID: `workstream-operator-control-plane`
- Thread ID: `workstream-operator-control-plane.operator-control-plane-phase-2-degraded-mode-and-portability-surface`
- Thread file: `docs/intent/workstreams/threads/workstream-operator-control-plane/06-operator-control-plane-phase-2-degraded-mode-and-portability-surface.md`
- Timestamp (UTC): `2026-05-04T09:19:42Z`
- Owner: `codex`

## Intent

Execute Wave 3 live parity validation using identical fixture payload and config snapshot across sqlite and bigquery backends, then capture evidence for no-drift Phase 2 closeout.

## Actions

- executed live sqlite run via `fitcv_cp.worker_job.execute_pipeline_run` with:
  - jobs path: `data/sample_data_engineer_jobs.json`
  - config path: `.env.yaml`
  - backend mode: `FITCV_CP_DATA_BACKEND=sqlite`
- executed live bigquery run via `fitcv_cp.worker_job.execute_pipeline_run` with the same jobs/config payload and:
  - backend mode: `FITCV_CP_DATA_BACKEND=bigquery`
  - credentials: `GOOGLE_APPLICATION_CREDENTIALS=C:/Users/HOANG PHI LONG DANG/repos/JOB-PROJECT/fitcv-491123-51c030d71e07.json`
- collected run summaries for both backends and generated explicit contract comparison output.

## Visible Output

- Evidence files:
  - `logs/parity-evidence-20260504/sqlite-run-summary.json`
  - `logs/parity-evidence-20260504/bigquery-run-summary.json`
  - `logs/parity-evidence-20260504/parity-comparison.json`
- Live run IDs:
  - sqlite: `parity-sqlite-00dfe208-db6d-4385-8dd0-352926285efa`
  - bigquery: `parity-bigquery-3bc2f257-651a-40f7-8d51-3574d2bd3363`
- Contract comparison (`parity-comparison.json`):
  - `status`: equal (`succeeded`)
  - `total_jobs`: equal (`10`)
  - `passed_filter`: equal (`4`)
  - `ranked`: equal (`4`)
  - `cvs_generated`: equal (`0`)
  - `results_export_present`: equal (`true`)
  - `stage_artifacts_present`: equal (`true`)
  - `events_count`: equal (`12`)
  - `event_stages`: equal (same ordered stage set)
  - overall parity: `true`

## Status

`pass`

## Next Decision

`continue`
