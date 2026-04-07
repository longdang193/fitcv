# FitCV Admin Control Plane

> An internal FastAPI administration UI and background-worker pipeline orchestrator for FitCV — a Gemini-powered job-to-CV matching system.

---

## Why

FitCV generates tailored CVs for job applications by:

1. Accepting a list of raw job postings
2. Enriching them with structured metadata (skills, seniority, domain, etc.) via Gemini
3. Matching them against a candidate profile using BigQuery vector search + AI scoring
4. Generating grounded CV markdown for the top-ranked jobs

The pipeline runs asynchronously in a background worker. Without a control plane, operating it required terminal access to trigger runs, check status, and inspect outputs.

This project adds an internal admin UI and a REST API so that pipeline runs can be managed without terminal access.

---

## What

The FitCV Admin Control Plane provides:

- **Trigger runs** — via file upload, pasted JSON, or path reference
- **Inspect runs** — status, events, enriched jobs, filter outcomes, CV downloads
- **Manage settings** — retrieval, timing, global filters, ranking, and CV generation settings through an admin UI backed by BigQuery key-value storage
- **Lifecycle controls** — stop/pause running runs, archive/unarchive completed runs

### Tech Stack

| Layer | Technology |
|---|---|
| Web framework | FastAPI |
| Templating | Jinja2 |
| Background jobs | RQ + Redis |
| Persistence | BigQuery |
| Pipeline AI | Gemini (Vertex AI) |
| Infrastructure | Docker + docker-compose |

### Architecture

```
Browser
  |
  | HTTP POST /admin/upload-trigger
  v
FastAPI server (src/fitcv_cp/)
  |  insert pipeline_runs row (status: queued)
  |  enqueue job to Redis
  v
Redis (RQ broker)
  |
  | RQ worker dequeues
  v
Worker (src/fitcv_cp/worker_job.py)
  |  reads effective_settings_json from run record
  |  calls run_pipeline(config=...)
  |  updates pipeline_runs status + events
  v
BigQuery (pipeline_runs, pipeline_run_events, cv_versions,
          structured_jobs, run_structured_jobs, rule_filter_results)
```

The web server and worker share state through BigQuery (append-only events + per-run snapshots) and Redis (job queue). The worker never re-reads live settings — it reads the immutable `effective_settings_json` snapshot captured at trigger time.

---

## Where

| Document | What it covers |
|---|---|
| `docs/generated/features_index.yaml` | Machine-friendly index of all features — start here for navigation |
| `docs/generated/feature_overview.md` | Human-readable feature summary and status |
| `docs/generated/stages_index.yaml` | Machine-friendly index of active stage contracts |
| `docs/generated/stage_overview.md` | Human-readable summary of active stage contracts |
| `docs/fitcv-control-plane-setup.md` | Local dev setup, Docker, troubleshooting |
| `docs/FitCV-pipeline.md` | High-level pipeline design (data engineering perspective) |
| `docs/features/<feature_id>/` | Per-feature contract, explanation, and history |
| `docs/stages/*.yaml` | Stage contract layer for adopted pipeline stages |
| `docs/superpowers/specs/` | Feature specs and design docs |
| `docs/superpowers/plans/` | Implementation plans |
| `.cursor/rules/operating-system/` | Project methodology: doc lifecycle, feature lifecycle, planning dispatch |

### Source layout

```
src/fitcv_cp/          # Control plane (FastAPI app)
  app.py               # Routes, trigger handlers, templates
  models.py            # RunStatus enum, PipelineRun, RunEvent dataclasses
  bq_store.py          # BigQuery reads/writes
  queue.py             # Redis/RQ queue setup
  worker_job.py        # RQ job: calls run_pipeline()
  reporter.py          # Pipeline event callbacks
  settings_schema.py   # Editable settings registry + validation
  settings_store.py    # BigQuery-backed settings read/write
  templates/           # Jinja2 admin pages
    base.html          # Layout + design system tokens
    runs_list.html     # /admin/runs
    run_detail.html    # /admin/runs/{id}
    settings.html      # /admin/settings

src/fitcv/             # Core pipeline (unchanged by control plane)
  pipeline.py          # run_pipeline() entrypoint
  enrich.py            # Gemini enrichment
  rule_filter.py       # Deterministic job filtering
  ranking.py           # BigQuery AI scoring + ranking
  cv_generator.py      # CV generation
  validator.py         # CV output validation
  config.py            # Config loading
```

### Key conventions

- **Run records are the source of truth.** `pipeline_runs` is inserted before any worker enqueue. If enqueue fails, the run sits in `queued` — the DB is never left in a half-committed state.
- **Settings are snapshotted at trigger time.** `effective_settings_json` captures the merged YAML + BQ + per-run-overrides config. The worker reads this snapshot, not live settings.
- **Snapshots are immutable.** `jobs_input_json` and `candidate_profile_json` on the run record are the canonical resolved inputs — never re-read from repo files at inspection time.
- **Enriched jobs are run-scoped.** `run_structured_jobs` preserves per-run enrichment data for debugging. The latest-state `structured_jobs` table is not used for run-detail inspection.
