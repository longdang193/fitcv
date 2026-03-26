# Admin Run Inspection and Per-Run JSON Inputs — Design Spec

**Date:** 2026-03-26  
**Status:** Draft  
**Feature area:** `src/fitcv_cp`, `src/fitcv`, `docs/superpowers`

---

## Problem

The admin run detail page currently shows enriched jobs and summary counts, but it does not explain why jobs were rejected by the deterministic rule filter. This makes runs with `0 passed` difficult to debug.

The admin trigger flow also only supports:

- jobs path
- jobs file upload

It does not support:

- pasted JSON jobs input
- candidate profile upload
- candidate profile pasted JSON
- inspection of the exact candidate profile used for a run

Because candidate profile loading still depends on `config["paths"]["candidate_profile"]`, there is no immutable run-scoped profile snapshot for audit or debugging.

---

## Goal

Add run-scoped inspection and per-run JSON input support so that:

1. rule-filter reject reasons are visible on the run detail page
2. the candidate profile used for a run is visible in both raw JSON and formatted views
3. admin-triggered runs can accept either file upload or pasted JSON for:
   - jobs input
   - candidate profile input
4. all run-specific inputs are immutable and auditable

---

## Non-Goals

- Global candidate profile management
- Replacing YAML candidate profiles throughout the pipeline
- Changing rule-filter policy itself
- Changing ranking or enrichment behavior
- Supporting YAML as pasted admin text input

---

## Product Decisions

### Candidate profile scope

Candidate profile overrides are **per-run only**.

Behavior:

- If the user does not provide a candidate profile override, the run uses the configured YAML path
- If the user uploads or pastes a candidate profile JSON, that snapshot is used only for that run
- Admin uploads do not overwrite repo-tracked YAML files

### Input UX

Jobs input and candidate profile input both use **dual inputs in one form** with explicit mode selection.

For jobs:

- `path`
- `upload`
- `paste`

For candidate profile:

- `default_config`
- `upload`
- `paste`

The selected mode determines which input is read. The server does not infer precedence from multiple populated fields.

---

## Current State

### Jobs input

- `/admin/upload-trigger` supports `jobs_path` and optional `jobs_file`
- uploaded jobs are written to `data/uploads/...json`
- no pasted jobs JSON input exists

### Candidate profile input

- pipeline loads profile from `config["paths"]["candidate_profile"]`
- no admin support exists for candidate upload or pasted JSON
- run detail page cannot show the profile used for a run

### Filter inspection

- rule-filter outcomes are stored in `rule_filter_results`
- the table is not currently run-scoped
- the admin UI does not render reject reasons

---

## User Experience

## Admin trigger page

The trigger form is expanded into two input groups.

### Jobs input group

Fields:

- `jobs_input_mode`
- `jobs_path`
- `jobs_file`
- `jobs_text`

Validation:

- `path` requires non-empty `jobs_path`
- `upload` requires a file
- `paste` requires valid JSON with top-level `list[object]`

### Candidate profile input group

Fields:

- `candidate_profile_mode`
- `candidate_profile_file`
- `candidate_profile_text`

Validation:

- `default_config` requires nothing extra
- `upload` requires a file containing valid candidate profile JSON
- `paste` requires valid candidate profile JSON text
- candidate profile JSON must satisfy the existing candidate validation contract

### Error behavior

Invalid inputs return `422` with a clear admin-visible message:

- invalid JSON
- wrong top-level type
- missing required candidate profile sections

---

## Run detail page

Add the following sections.

### Filter Outcomes

Per job, show:

- title
- filter status (`passed` or `rejected`)
- reject reasons

### Candidate Profile Used

Show two views:

- formatted readable view
- raw JSON view

### Jobs Input Used

Show:

- source type
- source path when applicable
- raw JSON snapshot when available
- graceful fallback when no snapshot exists

---

## Data Model Changes

## `pipeline_runs`

Add nullable columns:

- `jobs_input_source STRING`
- `jobs_input_json STRING`
- `candidate_profile_source STRING`
- `candidate_profile_json STRING`

Existing `jobs_path` remains.

Semantics:

- `jobs_input_source=path`: `jobs_path` points to source path, `jobs_input_json=NULL`
- `jobs_input_source=upload`: `jobs_path` points to saved upload, `jobs_input_json=NULL`
- `jobs_input_source=paste`: `jobs_path` points to saved pasted JSON file, `jobs_input_json` stores canonical JSON snapshot
- `candidate_profile_source=default_config`: `candidate_profile_json=NULL`
- `candidate_profile_source=upload|paste`: `candidate_profile_json` stores canonical JSON snapshot

## `rule_filter_results`

Add:

- `run_id STRING`

This is required so the admin UI can show reject reasons for the specific run being viewed.

---

## Runtime Configuration Changes

Per-run candidate profile override is injected into runtime config under:

- `config["runtime_inputs"]["candidate_profile_json"]`

Profile resolution order:

1. `runtime_inputs.candidate_profile_json`
2. `paths.candidate_profile`

This avoids overloading `paths.candidate_profile` with non-path content.

Runtime handshake:

1. `app.py` builds the effective config for the run
2. if a candidate override is supplied, `app.py` writes it into `effective_config["runtime_inputs"]["candidate_profile_json"]`
3. `insert_run(...)` stores that effective config snapshot in `pipeline_runs.effective_settings_json`
4. `worker_job.py` rehydrates `effective_settings_json` and passes that config into `run_pipeline`
5. `run_pipeline` resolves the candidate profile from `runtime_inputs.candidate_profile_json` before falling back to `paths.candidate_profile`

The run record is therefore not just audit metadata; it is the source of truth for the worker's runtime config snapshot.

---

## Public Interfaces

## `fitcv_cp.models.PipelineRun`

Add optional fields:

- `jobs_input_source`
- `jobs_input_json`
- `candidate_profile_source`
- `candidate_profile_json`

## `fitcv_cp.app._execute_trigger`

Expand internal arguments to carry:

- jobs input source
- jobs input snapshot
- candidate profile source
- candidate profile snapshot

## `fitcv.rule_filter.store_filter_results`

Change signature to:

- `store_filter_results(result, run_id, config)`

## New helper functions

### `fitcv.candidate.load_profile_json_text(payload: str) -> dict[str, Any]`

- parse JSON text
- validate top-level object
- return candidate profile dict

### `fitcv_cp.bq_store.list_filter_results_for_run(run_id, bq, project, dataset) -> list[dict[str, Any]]`

- query run-scoped filter results

---

## Persistence Rules

### Jobs pasted JSON

- validate as `list[object]`
- save a canonical JSON file under `data/uploads/{uuid}_pasted_jobs.json`
- store canonical pretty JSON in `jobs_input_json`
- set `jobs_path` to the saved file path

### Candidate uploaded or pasted JSON

- validate as `object`
- validate with existing candidate validation rules
- required sections are:
  - `experiences`
  - `skills`
  - `projects`
  - `achievements`
  - `preferences`
- store canonical pretty JSON in `candidate_profile_json`
- do not write YAML files

---

## Backward Compatibility

- Existing runs without new columns must still render gracefully
- Existing YAML-based candidate profile flow remains supported
- Existing file and path jobs flow remains unchanged
- If old runs do not have run-scoped filter rows, UI renders an unavailable state instead of guessing

---

## Error Handling

| Scenario | Behavior |
|---|---|
| Invalid jobs JSON | `422` |
| Invalid candidate JSON | `422` |
| Candidate validation errors | `422` with details |
| Missing candidate snapshot on old run | render fallback message |
| Missing jobs snapshot on old run | show source path only |
| Missing filter rows on old run | render unavailable state |
| BigQuery schema mismatch | explicit failure, no silent fallback |

---

## Acceptance Criteria

- A run with `0 passed` clearly shows which jobs were rejected and why
- A run detail page shows the candidate profile used by that run
- Candidate profile is visible in both raw JSON and formatted views
- Admin can trigger runs using jobs path, jobs upload, or pasted jobs JSON
- Admin can trigger runs using default candidate profile, candidate upload, or pasted candidate JSON
- Run-specific inputs are immutable and auditable
- No repo-tracked candidate YAML file is modified by admin operations

---

## Assumptions

- Candidate profile JSON shape matches the existing in-memory structure loaded from YAML
- JSON is the only supported pasted text format for new admin inputs
- Reject reason codes remain canonical backend strings for now
- Server-rendered HTML is sufficient; no frontend framework is required
