---
doc_id: usage
doc_type: operator-guide
explains:
  features:
    - cv_system
    - inspection_debugging
    - settings_system
    - trigger_run_management
  stages:
    - cv_analysis
    - cv_generation
    - ranking
---

# Usage

FitCV usage splits into FitCV Local operator usage, server operator usage, and
engineering usage.

## FitCV Local Flow

1. Launch **FitCV Local** from Start menu. Second launch reuses existing instance.
2. Complete onboarding if redirected to `/local/onboarding`. After setup, use
   **LLM & API** in navigation to edit provider/model routing, whole-run retry,
   and bounded prompt guidance on the same page.
3. Use each reset action to remove user override and return to packaged default.
4. Open `/admin/runs`, submit job input, and choose `Run All` or `Stage by Stage`.
5. Inspect progress, evidence, artifacts, settings used, and generated CV output.
6. Use **Data & Backup** for backup, import, or cold data relocation.
7. Use **System** for redacted diagnostics, version information, and shutdown.

Run submission stays disabled until candidate profile, provider routing, required
credential, and provider test are ready. Packaged executor accepts one active job;
concurrent submission receives visible busy response.

Diagnostics include allowlisted build, OS/runtime, redacted path, database,
provider host/model, readiness, and safe lifecycle log data. They exclude API
keys, authorization headers, profile content, prompts, job descriptions, CV text,
and raw database rows.

## Operator Flow

Entry point: `/admin/runs`

1. trigger a run (path/upload/paste)
2. choose run mode (`Run All` or `Stage by Stage`)
3. monitor events, stage progress, and lifecycle state
4. inspect run detail tabs and stage artifacts
5. export evidence (`export.json`, `cv-debug.json`, `settings-used.json`, stage artifacts, artifacts zip)

### Run Detail Overview Navigation

Run detail is now decision-first. Default view emphasizes status, outcome, warnings, next actions, stage snapshot, and effective-settings delta.

Workflow entry routes:

- synonym review workspace: `GET /admin/runs/{run_id}/synonym-review`
- artifacts workspace: run detail exports section (`GET /admin/runs/{run_id}` + `#run-exports-workspace`)

Diagnostics access:

- diagnostics section entry: `#diag-synonym-fingerprints`
- advanced diagnostics container: `#advanced-diagnostics`
- exports workspace anchor: `#run-exports-workspace`

Tooltip glossary semantics:

- `confidence`: model certainty for suggested mapping
- `triage mode`: freshness/reuse mode for recommendation decisions
- `suppressed`: proposal hidden by suppression policy or duplicate resolution
- `alias conflict`: alias already mapped to a different canonical value
- `run-scoped overlay`: override applies only to this run, not global defaults

Artifact truth note:

- run-scoped persisted artifacts/endpoints are source of truth
- local `artifacts/live_run_<run_id>/` is deterministic evidence mirror for portability/debug handoff
- backfill missing historical mirrors with:
  - `python scripts/backfill_live_run_artifacts.py --run-id <run_id> --dry-run`
  - `python scripts/backfill_live_run_artifacts.py --run-id <run_id>`

## Lifecycle Actions

Operator lifecycle actions are exposed through run-scoped admin routes:

- stop active run: `POST /admin/runs/{run_id}/stop`
- continue checkpointed run: `POST /admin/runs/{run_id}/continue`
- archive/unarchive run: `POST /admin/runs/{run_id}/archive`, `POST /admin/runs/{run_id}/unarchive`
- bulk archive/unarchive/cancel: `POST /admin/runs/bulk/archive`, `POST /admin/runs/bulk/unarchive`, `POST /admin/runs/bulk/cancel`
- reconciliation/repair when needed: `POST /admin/runs/{run_id}/repair-cancellation`
- bulk delete archived runs: `POST /admin/runs/bulk/delete-archived`

Archive and delete stay separate on purpose:

- `Archive` hides run from active view but keeps run detail, events, and exports.
- `Delete archived runs` is available only from `/admin/runs?view=archived`.
- delete uses `archived_at` age, defaults to `Older than 30 days`, submits threshold only, and relies on backend `deleted_count` for the final result.
- delete does not clear shared caches, embeddings, bookmarks, or settings.

## Preference Optimization

Use `/admin/optimization` after rating jobs with 1-5-star application interest.

1. Review evidence counts, active policy mode, and policy fingerprints.
2. Review **Rating Evidence** for up to 50 newest effective saved ratings, including run, job, saved baseline rank, baseline fit/label, and ordinal stars.
3. Select **Optimize Current Evidence** to create an inactive candidate.
4. Inspect solver, evaluation, coverage, and blocking reasons.
5. Activate or reject candidate manually with an operator label.
6. Roll back compatible learned policy to prior eligible snapshot or `zero_residual`.

All actions use redirect-after-POST. Page accepts no optimizer numeric parameters, and missing or stale evidence produces bounded notices rather than raw errors.

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

## Engineering Workflow

1. run app/worker in sqlite mode
2. reproduce/verify via live run
3. run focused tests
4. run contract/validator checks before merge

FitCV Local release smoke additionally covers health, onboarding, global CSRF,
second-instance reuse, shutdown, process exit, and fixed size/startup/memory budgets.

## Key Surfaces

- `GET /healthz`
- `POST /runs`
- `GET /runs/{run_id}`
- `GET /runs/{run_id}/events`
- `GET /admin/runs`
- `GET /admin/runs/{run_id}`
- `GET /admin/settings`
- `GET /admin/optimization`
- `GET /local/onboarding`
- `GET /local/data`
- `GET /local/system`

## Related Docs

- [setup.md](setup.md)
- [pipeline.md](pipeline.md)
- [architecture.md](architecture.md)


G# Modern Web Application (`/app`)

The modern FitCV application is available at `/app` (or `/app/#/<route>`):

1. **Overview (`#/overview`)**: System summary and fast access to workspaces.
2. **Candidate Profile (`#/candidate-profile`)**: Catalog and step-by-step profile creation wizard.
3. **Scans (`#/scans`*)*: Company scanner workflows, job collection, and output views.
4. **Runs (`#/runs`)**: Pipeline run execution, live event stream, and stage debugging.
5. **Job Evaluation (`#/job-evaluation`)**: Job fit evidence inspection and independent application interest rating.
6. **CV Review (`#/cv-review`*)*: Versioned tailored CV history, safe preview, decision recording, and download.
7. **Bookmarks (`#/bookmarks`)**: Saved job management and CSV export.
8. **Synonyms (`#/synonyms`)**: Skill/domain/role-family synonym editor and review queue.
9. **Personalization (`#/settings/personalization`)**: Baseline vs. personalized ranking configuration.
