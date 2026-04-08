# Run-Scoped Enrichment Inspection Design

## Problem

The pipeline already persists enriched job data to `structured_jobs`, but that table is keyed by `job_url` and represents the latest known enriched state for each posting. It does not preserve what a specific pipeline run produced at enrichment time.

This creates two problems in the admin experience:

- A run detail page cannot reliably explain why a run passed or rejected a job, because the enriched fields that informed rule filtering are not visible in the UI.
- Later runs can overwrite the same `job_url` in `structured_jobs`, which means ad hoc queries against the latest table are not a trustworthy explanation of what happened in a prior run.

## Goals

- Persist immutable, run-scoped enrichment outputs for every enriched job in a pipeline run.
- Allow admins to inspect the enrichment fields that drove filtering and ranking for a specific run.
- Keep the existing `structured_jobs` latest-state model intact for downstream pipeline joins and current behavior.

## Non-Goals

- Replacing `structured_jobs` as the canonical latest enriched jobs table.
- Rebuilding ranking or rule filtering behavior.
- Building a full analytics console for every pipeline stage.

## Proposed Approach

Introduce a new BigQuery table, `run_structured_jobs`, that stores one row per `run_id + job_url` using the same core enrichment fields already written to `structured_jobs`. The pipeline will continue writing to `structured_jobs` for latest-state behavior, and will additionally append run-scoped rows to `run_structured_jobs` immediately after enrichment.

The control plane will retrieve these run-scoped rows on the run detail page and render a compact inspection section showing the fields that matter for debugging:

- `title`
- `job_url`
- `location_type`
- `seniority`
- `job_family`
- `domain`
- selected skills such as `required_skills`

This should be paired with the already persisted `rule_filter_results` so the page can explain both:

- what the enrichment produced
- why the rule filter accepted or rejected each job

## Data Model

### New Table: `run_structured_jobs`

Recommended columns:

- `run_id STRING NOT NULL`
- `job_url STRING NOT NULL`
- `title STRING`
- `company_name STRING`
- `location STRING`
- `contract_type STRING`
- `experience_level STRING`
- `published_at DATE`
- `location_type STRING`
- `seniority STRING`
- `required_skills ARRAY<STRING>`
- `preferred_skills ARRAY<STRING>`
- `responsibilities ARRAY<STRING>`
- `domain STRING`
- `tech_stack ARRAY<STRING>`
- `years_experience_min INT64`
- `years_experience_max INT64`
- `keywords ARRAY<STRING>`
- `job_family STRING`
- `description_cleaned STRING`
- `enrichment_version STRING`
- `enrichment_model STRING`
- `enriched_at TIMESTAMP`

Primary logical key:

- `run_id + job_url`

Rationale:

- `structured_jobs` remains keyed by `job_url` for latest-state semantics.
- `run_structured_jobs` becomes the immutable audit/debug table for run-specific visibility.

## Pipeline Changes

After `enrich_batch(...)` completes, the pipeline will:

1. Continue calling `load_structured_jobs(enriched, config)` to maintain latest-state writes.
2. Call a new append-style persistence function that maps the same enriched rows into `run_structured_jobs` and adds the current `run_id`.

This new persistence step should happen before rule filtering so the exact enriched inputs to filtering are always captured.

## Control Plane Changes

### Data Access

Add a new store function in `src/fitcv_cp/bq_store.py`:

- `list_run_structured_jobs(run_id, ...)`

This will query `run_structured_jobs` by `run_id` and order rows consistently for display.

Optional but recommended:

- add a second helper that loads `rule_filter_results` for the same run via a join through the job URLs captured for that run
- or extend the existing route/store path to merge filter reasons into the returned row model

### Run Detail UI

Add a new section on the run detail page beneath the pipeline summary and above or below the event timeline:

- section title such as `Enriched Jobs`
- one row/card per enriched job
- visible fields:
  - title
  - link to job URL
  - `location_type`
  - `seniority`
  - `job_family`
  - `domain`
  - top required skills
  - rule filter outcome / reasons if available

This section should support both:

- successful runs with accepted jobs
- runs where `passed_filter = 0`, which is the most important debugging case

## Migration Strategy

Add a new checked-in DDL asset for `run_structured_jobs` and ensure it is part of the normal BigQuery bootstrap path. If the project needs a migration for already-bootstrapped environments, add a Python migration script consistent with the repo’s existing BigQuery migration pattern.

Avoid manual one-off SQL commands as the only deployment path.

## Testing Strategy

### Pipeline

- Add a test verifying the pipeline passes `run_id` into the run-scoped enrichment persistence function.
- Add a test verifying enriched rows are persisted both to `structured_jobs` and to `run_structured_jobs`.

### Control Plane Store

- Add tests for `list_run_structured_jobs(...)` using mocked BigQuery query results.

### Control Plane App/UI

- Add route/template tests verifying the run detail page renders run-scoped enrichment data.
- Add coverage for empty-state rendering when a run has no captured enrichment rows.
- Add coverage for a rejected-job case where enrichment is visible even when `passed_filter = 0`.

## Tradeoffs

### Why not only retrieve from `structured_jobs`?

Because `structured_jobs` is mutable latest-state storage. It is useful operationally, but it is not a trustworthy audit source for a specific historical run.

### Why not add `run_id` to `structured_jobs` and keep one table?

Because that blurs two separate responsibilities:

- latest current enrichment by `job_url`
- immutable per-run enrichment history

Keeping both concerns in one table makes the semantics harder to reason about and complicates existing joins that expect one current row per `job_url`.

## Recommendation

Implement `run_structured_jobs` plus run detail retrieval/rendering. This is the smallest design that gives reliable debugging visibility without disrupting the existing pipeline data model.
