# Feature Overview

> Generated — do not edit manually. Source: `docs/features/*/*.yaml`

## Active

| Feature | Version | Type | Owner | Summary |
|---|---|---|---|---|
| `admin_control_plane_core` | 1.0.0 | add | fitcv_cp | Internal admin UI and REST API to manage FitCV pipeline runs without terminal access. |
| `bounded_parallel_enrichment` | 1.0.0 | add | fitcv | Enrichment runs in bounded parallel batches with admin-controlled concurrency settings. |
| `cv_system` | 1.26.0 | add | fitcv | CV generation uses a structured preset-based configuration, keeps reranker fit as the sole post-filter fit authority, splits final-stage execution into `cv_analysis` and `cv_generation`, upgrades `cv_analysis` to hybrid lexical-plus-semantic domain and responsibility alignment with one bounded coverage-aware evidence bundle, validates structured and markdown sections against one shared section contract, grounds final-stage validation against the selected `cv_analysis` evidence bundle with deterministic hard-fact checks plus bounded soft-claim support, rejects unresolved placeholder headers such as `[Candidate Name]`, supports richer shortlist retrieval and reuse, emits stage-level quality metrics, reuses exact-match late-stage `ranking` AI-score rows plus exact-match `cv_analysis` records when their stage-owned fingerprints and contracts still match, centralizes prompt ownership plus config ownership under a clearer responsibility-based config room, treats the structured writer prompt as the sole active `cv_generation` runtime prompt contract, keeps `results.json` focused on the final per-job ledger while stage diagnostics live in stage artifacts, and keeps warning-only max-pages validation as the sole user-facing CV validation rule. |
| `inspection_debugging` | 2.21.0 | add | fitcv_cp | Admins can see what the pipeline did for a run, including shared stage progress for both `Run All` and `Stage by Stage`, paused staged checkpoints, enrich reuse provenance, selectable rule-filter marks, shortlist retrieval and embedding-reuse diagnostics, richer shortlist candidate-query components, explicit shortlist candidate-query reuse provenance, ranking contribution visibility and calibration surfaces, late-stage reuse diagnostics for `ranking` and `cv_analysis`, slimmer job-ledger exports, stage-local artifacts, compact severity-based run health with explicit `Pending` vs `N/A`, stage-gated export availability, a job-ledger `results.json` split from bundled stage diagnostics, outcome-first artifact samples, stable normalize timeline ownership, aggregate-first timeline summaries, distinct `cv_analysis` and `cv_generation` outcomes, multi-channel evidence-selection provenance, lexical-vs-semantic alignment detail, inputs used, generated CVs, explicit decision detail, hybrid validation provenance from deterministic and soft-claim grounding checks, canonicalized settings-used exports, clearer `cv-debug` coverage accounting, and prompt-id-based provenance for both ranking and the active structured-only `cv_generation` path. |
| `multi_file_job_input` | 1.0.0 | add | fitcv_cp | Admins can upload multiple JSON job files in one trigger request. |
| `pipeline_performance` | 1.6.0 | modify | fitcv | Reduced API costs by filtering jobs before enrichment, using reliable structured output parsing, centralizing enrich prompt management, reusing unchanged enrich results via fingerprints, reusing unchanged shortlist embeddings via a structured signature plus embedding contract, and trimming dead-weight operator-facing payloads and row-scaled timeline noise. |
| `run_lifecycle_controls` | 1.4.0 | add | fitcv_cp | Admins can stop queued, running, or paused `awaiting_continue` runs, archive or unarchive completed runs, apply lifecycle actions in bulk from the runs list, and rely on a server-owned max-runtime timeout guard whose diagnostics distinguish active runtime from Stage by Stage manual-wait time. |
| `settings_system` | 2.11.0 | add | fitcv_cp | Admins can view and edit pipeline tuning defaults through a task-first settings UI with clearer current-vs-draft feedback, basic-versus-advanced disclosure, denser CV output controls, and metadata-only treatment for fixed single-option runtime fields, while baseline defaults still resolve from centralized YAML/config ownership, persisted overrides still live in BigQuery, and operator-facing settings-used exports continue to present canonical settings instead of compatibility-era duplicate keys. |
| `trigger_run_management` | 2.15.0 | add | fitcv_cp | Admins can trigger runs via path reference, file upload, or pasted JSON in either `Run All` or `Stage by Stage` mode, attach a run-scoped synonym overlay before trigger for either mode, continue paused staged runs one stage at a time from persisted checkpoints, replace the run overlay after enrich before continuing into rule filter, cancel paused `awaiting_continue` runs when they should not resume, inspect shared stage progress from a selection-first runs list plus run detail, and export stage-owned artifacts once a stage has been reached in either mode. |
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

Each feature has a contract at `docs/features/<feature_id>.yaml` and optional focused docs under `docs/features/<feature_id>/`:

```text
docs/features/<feature_id>.yaml
docs/features/<feature_id>/history.md
```

For the machine-friendly index, see `docs/generated/features_index.yaml`.
