# Feature Overview

> Generated — do not edit manually. Source: `docs/features/<feature_id>/*.yaml`

## Active

| Feature | Version | Type | Owner | Summary |
|---|---|---|---|---|
| `admin_control_plane_core` | 1.0.0 | add | fitcv_cp | Internal admin UI and REST API to manage FitCV pipeline runs without terminal access. |
| `bounded_parallel_enrichment` | 1.0.0 | add | fitcv | Enrichment runs in bounded parallel batches with admin-controlled concurrency settings. |
| `cv_system` | 1.2.0 | add | fitcv | CV generation uses a structured preset-based configuration and is fully visible and editable from the admin settings UI. |
| `inspection_debugging` | 2.1.0 | add | fitcv_cp | Admins can see what the pipeline did for a run, including paused manual checkpoints, next-stage state, enriched jobs, filter outcomes, inputs used, generated CVs, and explicit stage-local decision detail from exports, stage artifacts, settings-used snapshots, and CV debug snapshots. |
| `multi_file_job_input` | 1.0.0 | add | fitcv_cp | Admins can upload multiple JSON job files in one trigger request. |
| `pipeline_performance` | 1.4.0 | modify | fitcv | Reduced API costs by filtering jobs before enrichment, using reliable structured output parsing, centralizing enrich prompt management, and reusing unchanged enrich results safely via raw-job and enrich-contract fingerprints. |
| `run_lifecycle_controls` | 1.0.0 | add | fitcv_cp | Admins can stop queued or running runs and archive or unarchive completed runs. |
| `settings_system` | 2.3.0 | add | fitcv_cp | Admins can view and edit pipeline tuning defaults through the admin UI, persisted in BigQuery. |
| `trigger_run_management` | 1.1.0 | add | fitcv_cp | Admins can trigger runs via path reference, file upload, or pasted JSON — and inspect runs from a status-aware list page. |
| `ui_consistency_theming` | 1.0.0 | add | fitcv_cp | Shared design system and dark/light theme toggle across all admin pages. |

## Dependency Graph

```text
admin_control_plane_core
├── cv_system
├── inspection_debugging
├── run_lifecycle_controls
├── settings_system
├── trigger_run_management
│   └── multi_file_job_input
└── ui_consistency_theming

pipeline_performance
└── bounded_parallel_enrichment
```

## Status Legend

- **planned** — concept exists; entry created with invariants and domains
- **building** — implementation underway
- **active** — post-execution review complete
- **deprecated** — replaced or removed

## Feature Contracts

Each feature has a contract and history at `docs/features/<feature_id>/`:

```text
docs/features/<feature_id>/
  <feature_id>.yaml   # structured truth — current state
  history.md          # changelog and post-execution reviews
```

For the machine-friendly index, see `docs/generated/features_index.yaml`.
