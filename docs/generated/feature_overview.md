# Feature Overview

> Generated — do not edit manually. Source: `docs/features/*/feature.source.yaml`


## Active

| Feature | Type | Owner | Summary |
|---|---|---|---|
| `admin_control_plane_core` | add | fitcv_cp | Internal admin UI and REST API to manage FitCV pipeline runs without terminal access. |
| `bounded_parallel_enrichment` | add | fitcv | Enrichment runs in bounded parallel batches with admin-controlled concurrency settings. |
| `cv_system` | add | fitcv | Own the grounded CV-writing path from post-ranking evidence preparation through `cv_analysis` and `cv_generation`, including evidence selection, fit-gate resolution, structured CV generation, validation against selected evidence, and the stage-owned artifacts that explain final CV outcomes.
 |
| `inspection_debugging` | add | fitcv_cp | Admins can see what the pipeline did for a run, including shared stage progress for both `Run All` and `Stage by Stage`, paused staged checkpoints, enrich reuse provenance, selectable rule-filter marks, shortlist retrieval and embedding-reuse diagnostics, richer shortlist candidate-query components, explicit shortlist candidate-query reuse provenance, ranking contribution visibility and calibration surfaces, late-stage reuse diagnostics for `ranking` and `cv_analysis`, slimmer job-ledger exports, compact per-job `results.json` rows, stage-local artifacts, compact severity-based run health with explicit `Pending` vs `N/A`, stage-gated export availability, a job-ledger `results.json` split from bundled stage diagnostics, outcome-first artifact samples, stable normalize timeline ownership, aggregate-first timeline summaries, explicit separation between reranker-blocked rows and true analyzed-and-skipped `cv_analysis` outcomes, truthful reranker-blocked propagation into compact `results.json` decision chains and `cv-debug` omission accounting, multi-channel evidence-selection provenance, lexical-vs-semantic alignment detail, inputs used, generated CVs, explicit decision detail, hybrid validation provenance from deterministic and soft-claim grounding checks, canonicalized settings-used exports, clearer `cv-debug` coverage accounting, and prompt-id-based provenance for both ranking and the active structured-only `cv_generation` path. |
| `multi_file_job_input` | add | fitcv_cp | Admins can upload multiple JSON job files in one trigger request. |
| `pipeline_performance` | modify | fitcv | Reduced API costs by filtering jobs before enrichment, using reliable structured output parsing, centralizing enrich prompt management, reusing unchanged enrich results via fingerprints, reusing unchanged shortlist embeddings via a structured signature plus embedding contract, extending bounded semantic lift to the most important `cv_analysis` fit channels, short-circuiting reranker `skip` jobs before expensive `cv_analysis` work, and trimming dead-weight operator-facing payloads, especially by tightening the `results.json` ledger boundary and row-scaled timeline noise. |
| `run_lifecycle_controls` | add | fitcv_cp | Admins can stop queued, running, or paused `awaiting_continue` runs, archive or unarchive completed runs, apply lifecycle actions in bulk from the runs list, and rely on a server-owned max-runtime timeout guard whose diagnostics distinguish active runtime from Stage by Stage manual-wait time. |
| `settings_system` | add | fitcv_cp | Admins can view and edit pipeline tuning defaults through a task-first settings UI with clearer current-vs-draft feedback, basic-versus-advanced disclosure, denser CV output controls, and metadata-only treatment for fixed single-option runtime fields, while baseline defaults still resolve from centralized YAML/config ownership, persisted overrides still live in BigQuery, and operator-facing settings-used exports continue to present canonical settings instead of compatibility-era duplicate keys. |
| `trigger_run_management` | add | fitcv_cp | Admins can trigger runs via path reference, file upload, or pasted JSON in either `Run All` or `Stage by Stage` mode, attach a run-scoped synonym overlay before trigger for either mode, continue paused staged runs one stage at a time from persisted checkpoints, replace the run overlay after enrich before continuing into rule filter, cancel paused `awaiting_continue` runs when they should not resume, inspect shared stage progress from a selection-first runs list plus run detail, and export stage-owned artifacts once a stage has been reached in either mode. |
| `ui_consistency_theming` | add | fitcv_cp | Shared design system and dark/light theme toggle across all admin pages. |

## Feature Contracts

Each managed feature uses the following shape:

```text
docs/features/<feature_id>/feature.source.yaml
docs/features/<feature_id>/<feature_id>.yaml
docs/features/<feature_id>/lineage.generated.yaml
docs/features/<feature_id>/history.md
```

For the machine-friendly index, see `docs/generated/features_index.yaml`.
