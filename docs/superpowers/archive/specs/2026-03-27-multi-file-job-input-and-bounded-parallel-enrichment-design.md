# Multi-File Job Input and Bounded Parallel Enrichment — Design Spec

**Date:** 2026-03-27
**Author:** Admin Control Plane
**Status:** Draft

---

## Problem

The current admin trigger flow accepts only one uploaded jobs JSON file per run.

This creates two practical limitations:

1. an admin cannot submit several job-data files as one logical run without manually merging them first
2. large runs take longer than necessary because enrichment is executed in a single sequential batch path

The current enrichment path already writes results to BigQuery, but BigQuery is only the storage layer. It is not the execution engine for enrichment. Parallelism therefore must be designed in the worker and enrichment code, not delegated to BigQuery.

---

## Goal

Add support for:

1. multiple uploaded jobs JSON files in one run
2. bounded parallel enrichment of the merged job set

The design should improve throughput for larger runs while preserving:

- one logical run id
- one run-scoped inspection surface
- deterministic run-scoped snapshots
- explicit rate-limit controls

---

## Non-Goals

- Using BigQuery as the enrichment execution engine
- Turning one logical run into many separate child runs in v1
- Unbounded concurrency
- Redesigning the entire ingestion model for every input mode
- Changing downstream ranking/filter semantics

---

## Design

### Input Model

The admin upload flow should support selecting multiple jobs JSON files for one run.

Recommended scope for v1:

- multi-file upload support for `upload` mode only
- keep `path` and `paste` modes unchanged

Each uploaded file must still contain a JSON array of job objects matching the current ingest expectations.

The system should treat all uploaded files as one logical jobs input for the run.

---

### Merge Model

Before pipeline execution, the uploaded files should be merged into one canonical run-scoped job payload.

Recommended behavior:

1. read each uploaded JSON file
2. validate that each file contains a JSON array
3. concatenate all job arrays
4. write one canonical merged JSON file into the existing run-scoped uploads area
5. use that merged file path as the run’s `jobs_path`

This preserves the current pipeline contract, which already expects one `jobs_path`.

Deterministic merge order should be explicit:

- preserve the order the files were submitted in
- preserve row order within each file

This makes the merged snapshot deterministic and easier to inspect.

---

### Snapshot Model

The run should store one immutable merged jobs snapshot for inspection.

Recommended behavior:

- `jobs_input_source` remains `upload`
- `jobs_input_json` stores the canonical merged JSON payload for the run
- the stored snapshot reflects the merged result, not each raw file independently

This keeps the run-detail inspection model simple and consistent.

Optional follow-up, not required for v1:

- store source file names separately for traceability

---

### Validation Rules

Each uploaded file should be validated before merge.

Validation expectations:

- file must decode as UTF-8 JSON
- top-level JSON value must be an array
- arrays may be empty, but the final merged payload must contain at least one job overall

Validation order should be explicit:

1. validate each uploaded file
2. reject the whole request if any file fails validation
3. only after all files validate successfully, merge them into the canonical payload

If any file is invalid:

- reject the whole trigger request
- return a clear error identifying which file failed validation

This keeps one run from mixing valid and invalid file fragments silently.

---

### Deduplication

The first implementation should rely on the existing normalization/deduplication path after ingest.

That means:

- file merge is concatenate-first
- normalization still handles duplicate jobs downstream

Do not add a second custom dedup layer during merge unless the existing normalization proves insufficient.

---

### Parallel Enrichment Model

Parallelism should be implemented in the enrichment layer or worker-side enrichment orchestration, not in BigQuery.

Recommended model:

- run cheap pre-enrichment global filters first
- split the pre-enrichment survivors into bounded batches
- enrich several batches concurrently
- preserve a configurable concurrency ceiling
- merge results back into one enriched result list before downstream storage

This is bounded parallel enrichment, not unbounded fan-out.

Parallel enrichment applies only after cheap pre-enrichment filtering has narrowed the candidate set.
The system should not parallel-enrich jobs that would already be rejected by pre-enrichment global filters.

---

### Concurrency Controls

Parallel enrichment must be explicitly configurable.

Recommended new config/settings:

- `enrichment_concurrency`
- `enrichment_batch_size`

Semantics:

- `enrichment_batch_size`: how many jobs are enriched in one worker batch unit
- `enrichment_concurrency`: how many batch units may run concurrently

These settings should remain admin-managed and conservative by default.

Recommended first defaults:

- `enrichment_batch_size = 10`
- `enrichment_concurrency = 1`

Exact defaults can be tuned later based on provider rate limits.
The first default should preserve the reliability characteristics of the previous sequential enrichment path.

Validation rules:

- both settings must be positive integers
- both settings should reject zero or negative values
- the implementation may also enforce conservative upper bounds

---

### Rate Limit and Failure Model

Parallel enrichment should still respect provider limits and preserve partial progress within a run.

Recommended rules:

- keep bounded concurrency low by default
- preserve the existing per-job or per-batch retry model where possible
- one failed job should not fail the whole run if the current enrichment contract already tolerates partial failures
- catastrophic provider/config failures may still fail the run

The implementation should remain explicit that throughput gains are constrained by upstream API/provider limits.
`enrichment_sleep_secs` should not be treated as a true global rate limiter once `enrichment_concurrency > 1`, because per-thread sleeping does not prevent multiple concurrent requests from overlapping.
Higher concurrency should therefore be treated as an admin-tuned optimization for providers and quotas that can tolerate it, not as a universally safe default.

If enrichment partially fails:

- each failed job must retain its stable identity
- the failure should be recorded with an enrichment failure state or reason
- failed jobs should be excluded from downstream steps that require enriched fields unless explicitly supported
- the rest of the run should continue when the current enrichment contract allows partial progress

---

### Ordering and Determinism

The run should still behave like one logical batch even when enrichment work is concurrent.

Recommended rules:

- merged input snapshot is deterministic
- downstream run-scoped writes still use the single `run_id`
- downstream correctness must not depend on concurrency-preserved list order
- final persisted enriched rows should be written in a deterministic order for inspection and downstream joins

If concurrent enrichment changes result ordering internally, the stored run-scoped rows should still be written in a deterministic order for admin display.

---

### Run Inspection Impact

Run detail should continue to work as one run.

Expected behavior:

- `Original Job Input` shows the canonical merged immutable upload snapshot for multi-file upload runs
- `Enriched Jobs` shows the combined enriched result set
- no child-run UI is introduced

If desired later, the UI may show a small metadata note such as:

- `Uploaded files: 3`

but that is optional for v1.

---

### Why BigQuery Is Not the Parallelism Layer

BigQuery should continue to store:

- raw jobs
- structured/enriched jobs
- run-scoped structured jobs

But enrichment execution itself still happens in Python before those writes.

Therefore:

- BigQuery can help scale storage and querying
- BigQuery does not replace worker-side bounded concurrency for the enrichment step

This distinction should stay explicit in implementation decisions.

---

## Acceptance Criteria

- [ ] Admin upload mode supports multiple jobs JSON files in one trigger request
- [ ] The system merges uploaded files into one canonical run-scoped jobs payload
- [ ] The run stores one immutable merged jobs snapshot in `jobs_input_json`
- [ ] Invalid uploaded files reject the whole request with a clear validation error
- [ ] The canonical merged payload preserves submitted file order and original row order within each file
- [ ] Existing normalization/deduplication remains the first dedup mechanism
- [ ] Enrichment parallelism is implemented in the worker/enrichment layer, not BigQuery
- [ ] Enrichment uses bounded concurrency with explicit config controls
- [ ] Enrichment concurrency and batch size are validated as bounded positive values
- [ ] Parallel enrichment runs only on jobs that survive pre-enrichment global filters
- [ ] Failed enrichment of individual jobs is captured without corrupting the rest of the run
- [ ] One run still produces one `run_id`, one run detail page, and one combined enriched jobs view
- [ ] Run-detail inspection remains compatible with merged multi-file uploads
- [ ] The design does not change downstream filtering or ranking semantics
