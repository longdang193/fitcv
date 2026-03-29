---
feature_type: modify
feature_name: trigger_run_management
status: draft
summary: "Add a run-scoped JSON export that bundles ordered jobs, enrichments, scores, and generated CV outputs."
invariants:
  - "Exports must be derived from immutable run-scoped snapshots and persisted run outputs, not current mutable source files."
  - "Export ordering must be deterministic and sorted by final score descending for scored jobs."
  - "The export endpoint must not require rerunning pipeline stages."
  - "The exporter must use a persisted run-scoped stable tie-breaker instead of incidental query order."
---

# Run Results JSON Export — Design Specification

Affected feature contract: [`docs/features/trigger_run_management/trigger_run_management.yaml`](../../features/trigger_run_management/trigger_run_management.yaml)

## Triage

Feature type: MODIFY
Summary: Add a downloadable run-results JSON artifact from the run detail page.
Reasoning: This extends the existing run-detail inspection and CV download experience with a broader export artifact, but does not create a separate product surface.
Invariants:
- Exports must reflect the specific run being viewed.
- Export data must include both ranked and non-ranked processed jobs when available.
- The export must preserve enough information for offline review without opening the admin UI.
- Export rows must be assembled only from persisted run-scoped data already associated with the run.
Dependencies:
- `admin_control_plane_core`
- `trigger_run_management`
- `cv_system`
Affected docs:
- feature_yaml: `docs/features/trigger_run_management/trigger_run_management.yaml`
- feature_history: `docs/features/trigger_run_management/history.md`
- feature_docs: none
- cross_cutting_docs: none
- readme: none
- generated: none
Generated refresh required: no
Spec needed: yes
Plan needed: yes
Risk level: medium

## Problem

Today the run detail page lets admins inspect results in-place and download individual CV markdown files. That is useful for one-off review, but weak for downstream usage.

Current gaps:

- no single artifact captures the full outcome of a run
- no easy way to export enriched job data together with ranking results
- no portable JSON bundle that includes generated CV content
- no offline artifact ordered by best result first

This makes it harder to:

- compare runs outside the UI
- hand results to another tool or teammate
- audit why certain jobs were ranked or skipped
- reuse generated CVs without multiple clicks

## Goals

- Add a run-scoped JSON export from the run detail page
- Include original and enriched job information in one artifact
- Include ranking scores and rank order
- Include generated CV content when available
- Sort exported rows from highest to lowest final score
- Make the export usable even when some jobs have no CV output

## Non-Goals

- Adding CSV, Excel, or ZIP export in this change
- Recomputing scores or regenerating CVs during export
- Exporting raw secret config values or credentials
- Building a separate “results warehouse” API outside the admin control plane

## Approaches Considered

### Option 1: Export ranked jobs only

Pros:

- smaller payload
- simplest mental model for “best results”

Cons:

- hides filter outcomes and near-misses
- makes debugging harder
- loses context for why only a subset was promoted

### Option 2: Export the full processed set with explicit statuses

Pros:

- best for auditability
- preserves ranked and non-ranked outcomes
- aligns with existing run-detail inspection model

Cons:

- larger payload
- requires clear status fields to avoid confusion

### Option 3: Separate exports for enriched jobs, scores, and CVs

Pros:

- very explicit separation
- smaller targeted downloads possible

Cons:

- more buttons and more user decisions
- forces downstream consumers to rejoin data manually

## Recommendation

Use Option 2.

The default export should be one JSON document for the whole run, with rows ordered by final score descending where scores exist, and with explicit per-job status markers so users can understand why some jobs have no CV.

This gives users one dependable artifact without hiding the rest of the pipeline outcome.

## User Experience

### Entry Point

Add a `Download Results JSON` button on the run detail page near the existing result actions.

### Button Behavior

- visible for completed runs
- enabled for `succeeded` runs
- optionally enabled for `failed` or `cancelled` runs only if enough run-scoped data exists to build a partial export
- downloads a `.json` file directly

### Filename

Recommended filename pattern:

`fitcv-run-<run_id>-results.json`

## Data Contract

The export should be a single JSON object with run metadata plus an ordered `results` array.

### Top-Level Shape

```json
{
  "run_id": "string",
  "status": "succeeded",
  "triggered_by": "admin",
  "created_at": "2026-03-29T16:08:55Z",
  "started_at": "2026-03-29T16:08:58Z",
  "finished_at": "2026-03-29T16:11:45Z",
  "jobs_path": "data/sample_jobs.json",
  "jobs_input_source": "upload",
  "summary": {
    "total_jobs": 7,
    "passed_filter": 3,
    "ranked": 2,
    "cvs_generated": 1
  },
  "results": []
}
```

### Per-Result Shape

Each element in `results` should include a stable superset of fields, with `null` used where data is unavailable.

`original_job` and `enriched_job` should reflect the persisted run-scoped inspection shapes already used by run detail. They should not be re-read from mutable source files or reconstructed ad hoc during export.

```json
{
  "job_url": "string",
  "job_title": "string",
  "company": "string",
  "location_type": "remote",
  "domain": "data_science",
  "original_job": {},
  "enriched_job": {},
  "pipeline_status": "ranked_with_cv",
  "reject_reasons": [],
  "scores": {
    "final_score": 0.91,
    "ai_score": 0.89,
    "vector_score": 0.76,
    "fit_label": "strong"
  },
  "rank": 1,
  "cv": {
    "version_id": "string",
    "fit_classification": "strong",
    "markdown": "# CV ...",
    "created_at": "2026-03-29T16:11:40Z"
  }
}
```

### Pipeline Status Values

Recommended normalized statuses:

- `rejected_before_enrichment`
- `rejected_after_enrichment`
- `passed_not_ranked`
- `ranked_no_cv`
- `ranked_with_cv`

These statuses should make it easy to interpret one row without cross-referencing the UI.

`pipeline_status` must be derived from persisted run-scoped facts such as filter outcome, enrichment presence, ranking presence, and CV presence. It must not be assigned through loose heuristic inference.

## Ordering Rules

The `results` array should be sorted in this order:

1. scored jobs, highest `final_score` to lowest
2. jobs with a persisted final ranking position but incomplete score payload
3. passed but not ranked jobs
4. rejected jobs

Tie-breakers:

1. lower numeric `rank`
2. higher `ai_score`
3. persisted run-scoped input-order index

The exporter must derive or persist a stable run-scoped input-order index from the canonical run snapshot or equivalent persisted run-scoped source. It must not rely on incidental query order.

This keeps the export deterministic and human-friendly.

## Data Sources

The export should be assembled from already-persisted run-scoped data rather than recomputing the pipeline.

Expected sources:

- `pipeline_runs` for run metadata and summary
- `pipeline_run_events` only if needed for fallback status enrichment
- immutable run input snapshots already stored on the run row
- run-detail inspection data that powers the existing enriched-jobs view
- `cv_versions` for generated CV metadata and markdown

## Backend Design

### New Read Model

Add a control-plane read path that assembles exportable run results into one response model.

Recommended responsibilities:

- fetch run metadata
- fetch enriched-job inspection rows for that run
- fetch any generated CV rows for that run
- join by stable job identity, preferably `job_url`
- normalize statuses and score fields
- sort rows deterministically

### New Endpoint

Recommended endpoint:

`GET /admin/runs/{run_id}/export.json`

Behavior:

- returns `404` if run does not exist
- returns `409` if run is still in progress
- returns `200` for completed runs with:
  - `Content-Type: application/json`
  - `Content-Disposition: attachment; filename="fitcv-run-<run_id>-results.json"`

## UI Design

The run detail page should expose the export near the existing result actions rather than hiding it inside a tab.

Recommended placement:

- same action row as `Refresh Status`
- or within the `Pipeline Results` panel when the run has completed

Recommended label:

- `Download Results JSON`

This should complement, not replace, the per-CV markdown download links.

The export endpoint should reuse the same admin authorization and access controls as the run detail page.

## Failure Handling

The export must still be useful when some parts are missing.

Rules:

- if a ranked job has no CV, include the job with `pipeline_status = "ranked_no_cv"`
- if a job was rejected, include reject reasons when available
- if a score field is unavailable, include `null`
- if the run lacks enough assembled data for a trustworthy export, fail clearly instead of silently fabricating rows

## Security and Privacy

The export must not include:

- raw service-account paths
- secret config values
- environment variables
- internal stack traces unless explicitly intended for admin diagnostics

Candidate and CV content may be sensitive, so the export remains an admin-only feature.

The export endpoint should follow the same admin access model already used for run detail.

## Test Strategy

- data-access tests for result assembly and sorting
- endpoint tests for `200`, `404`, and `409`
- template tests confirming the download button appears only in valid states
- regression test for mixed cases:
  - ranked with CV
  - ranked without CV
  - passed not ranked
  - rejected
- regression test that output order is highest to lowest `final_score`
- regression test that output ordering remains deterministic using a stable run-scoped tie-breaker
- regression test that export rows are assembled only from persisted run-scoped data associated with the run

## Open Questions

- Should partial exports be allowed for `failed` and `cancelled` runs, or only `succeeded` runs?
- Should the export include all processed jobs by default, or offer a future `ranked_only=true` option?
- Should `cv.markdown` always be included inline, or should we later support a lighter metadata-only export mode?

## Recommendation for First Implementation

For the first version:

- support succeeded runs only
- export the full processed set
- include inline CV markdown when present
- order by final score descending
- expose one button: `Download Results JSON`

That gives users the most useful artifact with the smallest UI surface area.

## Acceptance Criteria

- [ ] A succeeded run detail page exposes one `Download Results JSON` action
- [ ] The export is assembled only from persisted run-scoped data already associated with the run
- [ ] Export rows include original inspection shape, enriched inspection shape, normalized status, scores, and CV content when present
- [ ] Export ordering is deterministic and uses a stable run-scoped tie-breaker beyond score fields
- [ ] The downloaded response is served as `application/json` with an attachment filename of `fitcv-run-<run_id>-results.json`
