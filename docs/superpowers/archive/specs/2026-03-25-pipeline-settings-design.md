# Pipeline Settings Admin Page — Design

## Summary

Extend the FitCV Admin Control Plane with a settings page that lets an admin view and edit pipeline tuning defaults without modifying YAML files. Settings are stored in a BigQuery key-value table and applied to each pipeline run as an immutable snapshot, ensuring reproducibility.

## Goal

Allow an admin to:
1. View current active pipeline tuning values (BQ override or YAML default)
2. Edit any editable setting and persist it to BigQuery
3. Optionally override individual settings per-run at trigger time

## Non-Goals

- Do not expose model names, credentials, or infrastructure settings
- No real-time settings push to running jobs — settings are snapshotted at trigger time
- No role-based access control on the settings page (internal tool)
- No settings history UI — full history is queryable directly in BigQuery

## Architecture

### Config Precedence Chain

```
env.yaml + config/*.yaml (baseline)
    → pipeline_settings BQ table (global admin-editable defaults)
        → per-run overrides in POST /runs (one run only)
            → effective_config (immutable snapshot stored on pipeline_runs)
                → worker reads snapshot → run_pipeline(config=effective_config)
```

### Merge Responsibility

All merging happens in the **control plane layer** (`worker_job.py` and `POST /runs` handler). `run_pipeline()` receives a fully merged `config` dict and does not interact with BigQuery settings or overrides.

### Effective Config Snapshot

At trigger time (`POST /runs`):
1. Load YAML baseline via `load_config()`
2. Fetch current BQ settings (`load_active_settings(bq)`)
3. Apply per-run overrides from request body
4. Validate the merged result via `settings_schema.py`
5. Store as `effective_settings_json` on the `pipeline_runs` row
6. Enqueue only the `run_id`

The worker reads the stored `effective_settings_json` from the run record — it never re-reads BQ settings. This eliminates the race condition where settings change between trigger and execution.

## BigQuery Table — `pipeline_settings`

Append-only key-value table. "Current" value = latest row per key.

```sql
CREATE TABLE IF NOT EXISTS `{project}.{dataset}.pipeline_settings` (
  setting_key        STRING    NOT NULL OPTIONS(description="Namespaced key, e.g. pipeline.final_top_n"),
  setting_value_json STRING    NOT NULL OPTIONS(description="JSON-encoded value, e.g. 10 or 0.40"),
  updated_by         STRING,
  updated_at         TIMESTAMP NOT NULL
);
```

Values are stored as JSON strings (`"10"`, `"0.40"`) so any numeric type can round-trip without schema changes.

## Modified Table — `pipeline_runs` (add one column)

```sql
ALTER TABLE `{project}.{dataset}.pipeline_runs`
ADD COLUMN effective_settings_json STRING
OPTIONS(description="Merged config snapshot at trigger time: YAML + BQ + per-run overrides");
```

## Editable Keys (Settings Schema)

Keys are registered in `settings_schema.py`. The UI uses this registry as the single source of truth for display labels, types, defaults, and validation.

### Retrieval Group

| Key | Type | Default | Source |
|---|---|---|---|
| `pipeline.vector_search_top_n` | int | 50 | env.yaml `pipeline:` |
| `pipeline.ai_score_top_n` | int | 50 | env.yaml `pipeline:` |
| `pipeline.final_top_n` | int | 10 | env.yaml `pipeline:` |
| `pipeline.evidence_top_k` | int | 5 | env.yaml `pipeline:` |

### Timing / Throttling Group

| Key | Type | Default | Source |
|---|---|---|---|
| `enrichment_sleep_secs` | float | 1.0 | config/pipeline.yaml |
| `rerank_sleep_secs` | float | 0.5 | config/pipeline.yaml |

> Note: `rerank_top_n` is intentionally excluded — it is a fallback for direct `run_ai_scoring()` calls only. The pipeline always uses `pipeline.ai_score_top_n`.

### Ranking Policy Group

| Key | Type | Default | Source |
|---|---|---|---|
| `ranking_weights.ai_score` | float | 0.40 | config/ranking.yaml |
| `ranking_weights.must_have_match` | float | 0.20 | config/ranking.yaml |
| `ranking_weights.vector_similarity` | float | 0.15 | config/ranking.yaml |
| `ranking_weights.title_relevance` | float | 0.10 | config/ranking.yaml |
| `ranking_weights.seniority_fit` | float | 0.10 | config/ranking.yaml |
| `ranking_weights.preference_fit` | float | 0.05 | config/ranking.yaml |
| `fit_label_thresholds.strong` | float | 0.70 | config/ranking.yaml |
| `fit_label_thresholds.stretch` | float | 0.40 | config/ranking.yaml |
| `gap_thresholds.strong_min_matched_ratio` | float | 0.80 | gap_analysis.py `_DEFAULT_STRONG_RATIO` |
| `gap_thresholds.stretch_min_matched_ratio` | float | 0.50 | gap_analysis.py `_DEFAULT_STRETCH_RATIO` |

## Validation Rules

All rules are enforced in `settings_schema.py` and applied to both saved settings edits and per-run overrides.

### Per-field rules
- All int values ≥ 1
- All float values ≥ 0.0
- All threshold values in range [0.0, 1.0]
- Unknown keys rejected

### Relational rules (cross-field)
- `pipeline.final_top_n ≤ pipeline.ai_score_top_n ≤ pipeline.vector_search_top_n`
- `fit_label_thresholds.strong > fit_label_thresholds.stretch`
- `gap_thresholds.strong_min_matched_ratio > gap_thresholds.stretch_min_matched_ratio`
- `sum(ranking_weights.*) == 1.0` (± 0.01 tolerance)

Validation runs twice at trigger time: once after BQ merge, once after per-run overrides are applied.

## New Files

| File | Role |
|---|---|
| `src/fitcv_cp/settings_schema.py` | Registry of all editable keys: type, default, display label, group, validation rules |
| `src/fitcv_cp/settings_store.py` | BQ reads/writes for `pipeline_settings`; `load_active_settings()` returns merged dict |
| `src/fitcv_cp/templates/settings.html` | Admin settings form — grouped by Retrieval / Timing / Ranking Policy |
| `assets/bigquery/pipeline_settings.sql` | DDL for `pipeline_settings` table |
| `tests/fitcv_cp/test_settings_schema.py` | Unit tests for validation logic |
| `tests/fitcv_cp/test_settings_store.py` | BQ store tests with mocked client |

## Modified Files

| File | Change |
|---|---|
| `src/fitcv/pipeline.py` | Add `config: dict \| None = None` kwarg; if provided, skip internal `load_config()` |
| `src/fitcv_cp/worker_job.py` | Read `effective_settings_json` from run record; pass as `config=` to `run_pipeline()` |
| `src/fitcv_cp/app.py` | Add `GET /settings`, `POST /settings/{key}`, `GET /admin/settings`, `POST /admin/settings`; snapshot effective config before enqueue in `POST /runs` |
| `src/fitcv_cp/bq_store.py` | `insert_run()` and `_row_to_run()` handle new `effective_settings_json` field |
| `assets/bigquery/pipeline_runs.sql` | Add `effective_settings_json STRING` column |

## API Endpoints

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/settings` | Return current active settings (BQ overrides merged with YAML defaults) |
| `POST` | `/settings/{key}` | Persist a new value for a single key to `pipeline_settings` |
| `GET` | `/admin/settings` | HTML form showing all editable keys grouped by category |
| `POST` | `/admin/settings` | Form submit — validates and saves updated settings |

`POST /runs` body gains an optional `config_overrides` field:
```json
{
  "jobs_path": "data/sample_jobs.json",
  "config_overrides": {
    "pipeline.final_top_n": 5,
    "ranking_weights.ai_score": 0.50
  }
}
```

Same whitelist and validation as the settings page.

## Admin UI — Settings Page

`GET /admin/settings` renders a form with three sections:

**Retrieval** — vector_search_top_n, ai_score_top_n, final_top_n, evidence_top_k

**Timing / Throttling** — enrichment_sleep_secs, rerank_sleep_secs

**Ranking Policy** — ranking_weights (6 inputs), fit_label_thresholds (2 inputs), gap_thresholds (2 inputs)

Each field shows:
- Display label (friendly)
- Current active value (BQ override highlighted if active, YAML default shown as hint)
- Input box for new value
- Validation error message inline if invalid

Ranking weights section shows a live "sum" indicator so the admin can see when weights drift from 1.0.

## How Config Keys Are Applied to `run_pipeline()`

The `settings_schema.py` registry knows how to write each editable key back into the nested config dict shape that `run_pipeline()` expects:

| Settings key | Config dict path |
|---|---|
| `pipeline.vector_search_top_n` | `config["pipeline"]["vector_search_top_n"]` |
| `enrichment_sleep_secs` | `config["enrichment_sleep_secs"]` |
| `ranking_weights.ai_score` | `config["ranking_weights"]["ai_score"]` |
| `fit_label_thresholds.strong` | `config["fit_label_thresholds"]["strong"]` |
| `gap_thresholds.strong_min_matched_ratio` | `config["gap_thresholds"]["strong_min_matched_ratio"]` |

This mapping lives in `settings_schema.py` so neither `app.py` nor `worker_job.py` need to know the internal config structure.

## Verification

### Automated tests
- `test_settings_schema.py`: all validation rules, relational constraints, key whitelist, type coercion
- `test_settings_store.py`: BQ reads/writes with mocked client; `load_active_settings()` returns correct merged dict
- `test_app.py`: `GET /settings`, `POST /settings/{key}`, `POST /runs` with `config_overrides`; invalid overrides return 422

### Manual smoke test
1. Open `http://localhost:8000/admin/settings`
2. Change `pipeline.final_top_n` to 5
3. Trigger a run via `POST /runs`
4. Check `pipeline_runs.effective_settings_json` — should show `final_top_n: 5`
5. Verify the run used top-5 instead of top-10
