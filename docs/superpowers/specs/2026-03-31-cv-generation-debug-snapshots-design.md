---
feature_type: modify
feature_name: inspection_debugging
status: draft
summary: "Add run-scoped CV-generation debug snapshots so admins can inspect immediate per-job generation artifacts without rerunning the pipeline."
invariants:
  - "Debug snapshots must be derived only from the actual run-scoped CV generation path; no recomputation."
  - "Debug artifacts must remain separate from the existing final run-results export."
  - "Snapshot storage must be bounded so large runs do not produce unbounded debug payloads."
  - "Debug capture must not block normal successful CV generation when snapshot persistence fails."
  - "Every snapshot field must be captured from the live run path at the stage where it existed; later reconstruction from final persisted outputs is not allowed."
---

# CV Generation Debug Snapshots

## Context

We already persist and expose a final run-scoped artifact through `Download Results JSON`, plus stage events in the event timeline. That is useful for outcome inspection, but it is still weak for CV-generation debugging.

Recent debugging sessions exposed repeated cases where we had to infer the CV-generation failure point indirectly:

- a ranked job produced no CV, but the UI only showed `ranked_no_cv`
- a CV existed, but a section looked too shallow or too repetitive
- a generated CV differed unexpectedly between runs, yet the immediate structured generation result was not visible
- validation, repair, rendering, and persistence failures had to be reconstructed from logs and code instead of a run-scoped artifact

The root gap is:

- we persist final results well
- we persist some stage facts in separate tables
- but we do **not** persist a compact run-scoped debug snapshot of the **immediate CV-generation process result**

That makes CV debugging slower than it should be.

## Problem

For a ranked job, the current system can tell us:

- the job was ranked
- the final CV was or was not generated
- the final exported CV and metadata if generation succeeded

But it usually cannot show, in one run-scoped place:

- the evidence that actually went into CV generation
- the gap summary used for fit classification
- the first structured CV returned by the model
- the first validation result
- whether repair/retry happened
- the final accepted structured CV / markdown pair
- the exact intermediate payload when CV generation failed

This forces debugging to rely on:

- scattered stage tables
- textual event messages
- container logs
- re-reading code to infer what likely happened

## Goal

Add a bounded run-scoped debug artifact for the CV-generation process so an admin can inspect the immediate per-job generation result for ranked jobs without rerunning the pipeline.

## Non-Goals

- Replacing the existing final `Download Results JSON` export
- Capturing every prompt token or full raw model request/response by default
- Building a full prompt-debugging console in this rollout
- Redesigning run detail or the CV export UX broadly

## Why A New Artifact Is Needed

The current final export is outcome-oriented. It answers:

- what jobs were processed
- what scores they got
- what final CV was accepted

It does **not** answer:

- what the model first produced before validation/repair
- what validation saw
- what repair attempted to fix
- what immediate structured generation state existed when a CV failed

Those are debugging questions, not delivery questions. They deserve a separate artifact.

## Options Considered

### Option 1: Rely only on existing event messages and stage tables

Rejected.

Why:

- event messages are mostly text, not rich structured payloads
- several stage tables are not convenient run-scoped debug surfaces
- reconstructing one ranked job’s CV-generation path still takes too much manual work

### Option 2: Store giant raw prompts and raw model responses for every successful CV

Rejected for first rollout.

Why:

- too heavy
- higher privacy and storage cost
- easy to over-log low-signal noise
- not necessary to solve the current debugging pain

### Option 3: Persist bounded run-scoped per-job CV-generation debug snapshots

Recommended.

Why:

- captures the immediate CV-generation state we actually need
- remains separate from the final delivery export
- can be bounded to ranked jobs and high-signal payloads
- supports both success-path and failure-path debugging

## Recommended Design

Persist a run-scoped JSON snapshot containing per-ranked-job CV-generation debug records.

Each record should capture the immediate generation process for one ranked job, including:

- evidence summary used for generation
- gap summary and fit classification
- initial structured CV output from the model
- initial validation result
- repair attempt metadata if applicable
- final accepted structured CV / markdown if generation succeeds
- failure details if generation fails

This artifact should be stored separately from `results_export_json`.

## Proposed Artifact Shape

Top-level run-scoped payload:

```json
{
  "run_id": "10370cee-3155-45d8-80d9-7c6800b62114",
  "status": "succeeded",
  "debug_schema_version": "cv_generation_debug_v1",
  "created_at": "2026-03-31T22:24:36Z",
  "ranked_jobs_total": 2,
  "debug_records_captured": 2,
  "snapshot_complete": true,
  "debug_records": [
    {
      "job_url": "https://example.com/job-1",
      "job_title": "Senior Data Analyst",
      "fit_classification": "strong",
      "evidence_used": [
        {
          "evidence_type": "experience_entry",
          "source_ref": "experience[1]",
          "name": "Data Engineer at Fintech Startup GmbH"
        }
      ],
      "gap_summary": {
        "matched": ["SQL", "Python"],
        "missing": ["dbt"]
      },
      "structured_cv_initial": {
        "schema_version": "cv_doc_v1",
        "sections": {
          "experience": []
        }
      },
      "validation_initial": {
        "valid": false,
        "missing_sections": ["summary"]
      },
      "repair_attempt": {
        "performed": true,
        "missing_sections": ["summary"]
      },
      "structured_cv_final": {
        "schema_version": "cv_doc_v1",
        "sections": {
          "summary": {
            "text": "..."
          }
        }
      },
      "markdown_final": "# Candidate Name\n...",
      "status": "accepted"
    },
    {
      "job_url": "https://example.com/job-2",
      "job_title": "Data Quality Analyst",
      "fit_classification": "stretch",
      "evidence_used": [],
      "gap_summary": {},
      "structured_cv_initial": null,
      "validation_initial": null,
      "repair_attempt": {
        "performed": false,
        "missing_sections": []
      },
      "structured_cv_final": null,
      "markdown_final": null,
      "status": "persistence_failed",
      "error": {
        "stage": "store_cv_version",
        "message": "BigQuery insert errors for cv_versions: ..."
      }
    }
  ]
}
```

## Record Semantics

Unless otherwise stated below, keys are required and may be explicitly `null` when the artifact did not exist.

### `evidence_used`

Purpose:

- show the actual evidence items that entered CV generation for that job

For first rollout:

- store a compact evidence summary, not every full evidence field
- include enough to identify what grounded the CV
- preserve identifiers and short selected context, not full free-text evidence payloads

Minimum fields:

- `evidence_type`
- `source_ref`
- `name`

Optional when useful:

- `skills`
- selected highlights

Boundedness rule for first rollout:

- preserve only the bounded evidence set that actually entered CV generation for that job
- do not include full prompt text
- do not include arbitrary unbounded nested source payloads

### `structured_cv_initial`

Purpose:

- preserve the model’s immediate structured CV output before repair or final acceptance

Rules:

- store the normalized structured document that came back from generation
- do not regenerate it later
- if generation fails before structured output exists, use `null`
- this key is required even when value is `null`

### `validation_initial`

Purpose:

- show what the first validation pass concluded

Expected fields:

- `valid`
- `missing_sections`
- `grounding_violations`
- `skill_violations`
- `warnings`

Rules:

- this key is required
- if validation never ran, value is `null`

### `repair_attempt`

Purpose:

- make repair/retry behavior explicit instead of implicit

Expected fields:

- `performed`
- `missing_sections` when applicable

Rules:

- this key is required
- it should always be an object, never omitted
- if no repair path was attempted, use:

```json
{
  "performed": false,
  "missing_sections": []
}
```

### `structured_cv_final` and `markdown_final`

Purpose:

- preserve the final accepted artifact after any repair and validation steps

Rules:

- these are the final accepted values, not independently recomputed ones
- if the CV fails before acceptance, these remain `null`

Justification for keeping both:

- `structured_cv_final` is needed to inspect semantic generation, repair, and validation behavior
- `markdown_final` is needed to inspect render-path issues without requiring a second lookup elsewhere

Both are acceptable in v1 because the artifact is limited to ranked jobs and remains admin-debug oriented.

### `status`

Recommended values:

- `accepted`
- `validation_failed`
- `generation_failed`
- `persistence_failed`
- `skipped` only if the implementation includes ranked-job records that entered the CV-generation path but were intentionally not generated

This is intentionally narrower than the full run-results status taxonomy because this artifact is specific to the CV-generation path.

Status rules:

- `accepted`
  - final structured CV and final markdown exist and were accepted for this run path
  - repair may or may not have happened
- `validation_failed`
  - generation produced an initial artifact, but no final accepted CV survived validation
- `generation_failed`
  - the CV-generation step failed before a usable initial structured CV could be accepted
- `persistence_failed`
  - final accepted artifact existed in memory, but storing the CV artifact failed
- `skipped`
  - only allowed if the implementation intentionally captures ranked jobs that entered this path but were deliberately not generated

If `skipped` is not used in the implementation, it should be omitted entirely from the runtime status set rather than inferred loosely.

### `error`

Purpose:

- preserve the final failure detail for non-accepted records without requiring log lookup

Rules:

- this key is required
- value is `null` for `accepted`
- for non-accepted states, preserve at least:
  - `stage`
  - `message`

## Required Record Contract

Each debug record must contain these keys:

- `job_url`
- `job_title`
- `status`
- `fit_classification`
- `evidence_used`
- `gap_summary`
- `structured_cv_initial`
- `validation_initial`
- `repair_attempt`
- `structured_cv_final`
- `markdown_final`
- `error`

Nullability rules:

- `fit_classification`: nullable when unavailable
- `gap_summary`: nullable when unavailable
- `structured_cv_initial`: nullable
- `validation_initial`: nullable
- `structured_cv_final`: nullable
- `markdown_final`: nullable
- `error`: nullable

Non-null required shapes:

- `evidence_used`: always an array, possibly empty
- `repair_attempt`: always an object

## Storage Options

### Recommended first rollout

Add a new nullable field on `pipeline_runs`:

- `cv_generation_debug_json STRING`

Why:

- mirrors the existing `results_export_json` pattern
- easy to fetch on run detail
- cleanly run-scoped
- no join-heavy reconstruction path

### Not recommended for first rollout

Create a full new row-per-job debug table immediately.

That may become useful later, but it is more schema-heavy than needed for the first debugging slice.

Tradeoff note:

- this JSON field is appropriate for a first run-scoped debugging surface
- it is not ideal for cross-run analytics, large-scale querying, or incremental per-job writes
- if those become important later, a dedicated table may be a better second-step design

## Capture Policy

To keep the artifact bounded, the first rollout should **not** capture everything forever.

Recommended policy:

- capture only ranked jobs
- capture compact evidence summaries, not full raw prompts
- capture all ranked jobs when ranked count is small and normal
- if ranked count grows large later, cap or trim debug detail conservatively

### Strong recommendation

For first rollout, always capture debug records for ranked jobs.

Why:

- ranked jobs are already the narrow expensive path
- this is where most CV debugging value is
- keeping capture deterministic makes debugging simpler than conditional capture rules

## Partial Snapshot Semantics

Partial capture is allowed.

This can happen if:

- the run crashes after some ranked-job records were assembled
- worker termination happens before full snapshot persistence completes
- some ranked jobs produced debug records before a later fatal interruption

Top-level required fields:

- `ranked_jobs_total`
- `debug_records_captured`
- `snapshot_complete`

Interpretation:

- `ranked_jobs_total` = total ranked jobs the run intended to send through the CV-generation path
- `debug_records_captured` = number of debug records actually persisted into the snapshot
- `snapshot_complete = true` only when all intended ranked-job records were captured in the artifact

This makes partial snapshots interpretable instead of ambiguous.

## Boundedness And Truncation Policy

If serialized snapshot size exceeds internal limits:

- trim low-priority large fields before dropping records
- preserve all identifiers, statuses, compact evidence references, and error stage/message fields
- prefer truncating large markdown or large nested debug text before removing whole job records

Priority order:

1. keep:
   - top-level run metadata
   - `ranked_jobs_total`
   - `debug_records_captured`
   - `snapshot_complete`
   - per-record `job_url`
   - per-record `status`
   - per-record `error`
   - compact `evidence_used`
2. trim next:
   - large `markdown_final`
   - oversized nested text fields inside structured artifacts when necessary
3. drop whole records only as a last resort

The implementation may choose exact size thresholds, but this trimming order is part of the contract.

## Relationship To Existing Run Export

The final run-results export remains the delivery-oriented artifact.

The new debug snapshot is:

- debugging-oriented
- intermediate-state aware
- not intended as the primary export for downstream reuse

This separation is important:

- delivery export should stay readable and portable
- debug snapshot can carry validation/repair/process details without polluting the main export

The debug snapshot is not a downstream delivery artifact and must not become the canonical export surface for normal run consumption.

## Relationship To Event Timeline

The event timeline should continue to show concise stage messages.

This feature should not dump giant debug payloads into `pipeline_run_events.message`.

Instead:

- the event timeline can link conceptually to debug records
- `payload_json` may carry small references or compact summaries
- the full per-job debug artifact should live in the dedicated run-scoped snapshot

This snapshot is a debugging convenience surface, not the long-term system of record for every stage fact.

## Failure Handling

If debug snapshot persistence fails:

- the normal run should still succeed if the CV itself succeeded
- log a warning
- do not downgrade the run to failed purely because debug capture failed

This matches the current resilience pattern used for the final run-results export snapshot.

## Security And Privacy

This artifact may contain:

- generated CV content
- evidence summaries
- candidate-derived content

So it should follow the same admin-only access model as run detail and results export.

It should **not** capture:

- raw service-account data
- unrelated secrets
- arbitrarily large raw prompt dumps in the first rollout

## Affected Components

Likely code areas:

- [`src/fitcv/pipeline.py`](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/src/fitcv/pipeline.py)
  - assemble per-job debug records during Layer 4
- [`src/fitcv_cp/worker_job.py`](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/src/fitcv_cp/worker_job.py)
  - persist run-scoped debug snapshot on success
- [`src/fitcv_cp/bq_store.py`](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/src/fitcv_cp/bq_store.py)
  - store/read new snapshot field
- [`assets/bigquery/pipeline_runs.sql`](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/assets/bigquery/pipeline_runs.sql)
  - add debug snapshot column
- [`src/fitcv_cp/app.py`](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/src/fitcv_cp/app.py)
  - expose download endpoint
- [`src/fitcv_cp/templates/run_detail.html`](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/src/fitcv_cp/templates/run_detail.html)
  - expose one minimal admin action if included in rollout

## UI Scope

First rollout should expose:

- one admin-only download action for the debug snapshot

First rollout should **not** require:

- a broad new inspection panel
- a redesigned run-detail layout
- embedded full debug rendering in the run page

A minimal inline affordance may be added later, but the v1 contract is download-first.

## Affected Feature Contracts

Primary feature:

- [`docs/features/inspection_debugging/inspection_debugging.yaml`](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/features/inspection_debugging/inspection_debugging.yaml)

Related feature:

- [`docs/features/cv_system/cv_system.yaml`](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/features/cv_system/cv_system.yaml)

Potential downstream UI/export touchpoint:

- [`docs/features/trigger_run_management/trigger_run_management.yaml`](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/features/trigger_run_management/trigger_run_management.yaml)

## Risks

### Storage bloat

Mitigation:

- ranked jobs only
- compact evidence summaries
- no full raw prompt dumps in first rollout
- bounded truncation policy when snapshot size grows too large

### Debug artifact becomes a second main export

Mitigation:

- keep it explicitly admin-debug oriented
- keep final run export as the primary delivery artifact

### Persistence failures interfere with successful runs

Mitigation:

- make debug persistence best-effort
- warn, do not fail the run

## Acceptance Criteria

- [ ] A completed run can persist a run-scoped CV-generation debug snapshot without rerunning CV generation
- [ ] Debug records exist only for actual ranked jobs from that run
- [ ] Each debug record includes the immediate structured CV result when one existed
- [ ] Each debug record includes the first validation result
- [ ] Repair/retry behavior is explicit when it occurred
- [ ] Final accepted structured CV / markdown values are preserved separately from initial generation output
- [ ] Failure-path records can show where CV generation failed even when no final CV was accepted
- [ ] Debug snapshot persistence failure does not cause the whole run to fail
- [ ] The final `results_export_json` artifact remains separate and unchanged in purpose
- [ ] Snapshot fields are captured from the live run path where they existed, not reconstructed later from final persisted outputs
- [ ] Partial snapshots are interpretable through `ranked_jobs_total`, `debug_records_captured`, and `snapshot_complete`
- [ ] Boundedness/truncation does not remove core identifiers, statuses, or error stage/message fields
- [ ] First rollout UI scope is limited to an admin debug-download action rather than a broad run-detail redesign

## Recommendation

Proceed with a bounded run-scoped `cv_generation_debug_json` snapshot on `pipeline_runs`.

This is the smallest change that gives us a real debugging surface for immediate CV-generation state without polluting the delivery-oriented run export or relying on giant event payloads.
