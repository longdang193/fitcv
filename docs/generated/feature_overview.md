# Feature Overview

> Generated — do not edit manually. Source: `docs/features/<feature_id>/*.yaml`

## Active

| Feature | Version | Type | Owner | Summary |
|---|---|---|---|---|
| `admin_control_plane_core` | 1.0.0 | add | fitcv_cp | Internal admin UI and REST API to manage FitCV pipeline runs without terminal access. |
| `bounded_parallel_enrichment` | 1.0.0 | add | fitcv | Enrichment runs in bounded parallel batches with admin-controlled concurrency settings. |
| `cv_system` | 1.18.0 | add | fitcv | CV generation uses a structured preset-based configuration, split `cv_analysis` and `cv_generation` stages, shortlist retrieval that stays latest-only while reusing unchanged job embeddings safely, now builds richer shortlist candidate queries and reuses the single candidate-query embedding when safe, and keeps final-stage validation grounded to selected `cv_analysis` evidence before persistence. |
| `inspection_debugging` | 2.10.0 | add | fitcv_cp | Admins can see what the pipeline did for a run, including shortlist query/reuse diagnostics, ranking contribution visibility, stage-local artifacts, multi-channel evidence-selection provenance, and hybrid validation provenance from deterministic and soft-claim grounding checks. |
| `multi_file_job_input` | 1.0.0 | add | fitcv_cp | Admins can upload multiple JSON job files in one trigger request. |
| `pipeline_performance` | 1.5.0 | modify | fitcv | Reduced API costs by filtering jobs before enrichment, using reliable structured output parsing, centralizing enrich prompt management, reusing unchanged enrich results via fingerprints, and reusing unchanged shortlist embeddings via a structured signature plus embedding contract. |
| `run_lifecycle_controls` | 1.0.0 | add | fitcv_cp | Admins can stop queued or running runs and archive or unarchive completed runs. |
| `settings_system` | 2.5.0 | add | fitcv_cp | Admins can view and edit pipeline tuning defaults through the admin UI, including richer ranking calibration surfaces, persisted in BigQuery. |
| `trigger_run_management` | 2.3.0 | add | fitcv_cp | Admins can trigger runs via path reference, file upload, or pasted JSON, run the pipeline automatically or stage by stage, and inspect richer shortlist debug state in run exports. |
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
