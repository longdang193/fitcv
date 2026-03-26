# Admin Run Inspection and Per-Run JSON Inputs — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add run-scoped filter inspection and per-run JSON input support so the admin UI can show reject reasons, inspect the candidate profile used for a run, and trigger runs with either file upload or pasted JSON for both jobs and candidate profile.

**Architecture:** Extend `pipeline_runs` with run-scoped input metadata and snapshots, make `rule_filter_results` run-scoped by adding `run_id`, support runtime candidate profile JSON override in the pipeline, and expand the admin UI and BQ helpers to render inspection data.

**Tech Stack:** Python, FastAPI, Jinja2, BigQuery, pytest

**Spec:** `docs/superpowers/specs/2026-03-26-admin-run-inspection-and-json-inputs-design.md`

---

## File Map

- **Modify:** `src/fitcv_cp/models.py`
- **Modify:** `src/fitcv_cp/bq_store.py`
- **Modify:** `src/fitcv_cp/app.py`
- **Modify:** `src/fitcv_cp/templates/runs_list.html`
- **Modify:** `src/fitcv_cp/templates/run_detail.html`
- **Modify:** `src/fitcv/rule_filter.py`
- **Modify:** `src/fitcv/pipeline.py`
- **Modify:** `src/fitcv/candidate.py`
- **Modify:** `tests/test_fitcv_cp/test_app.py`
- **Modify:** `tests/test_fitcv_cp/test_bq_store.py`
- **Modify:** `tests/test_rule_filter.py`
- **Modify:** `tests/test_pipeline.py`
- **Modify:** `tests/test_candidate.py`
- **Add:** BigQuery migration for `pipeline_runs`
- **Add:** BigQuery migration for `rule_filter_results`

---

## Task 1: Add Run-Scoped Persistence Fields

**Files:**

- Modify: `src/fitcv_cp/models.py`
- Modify: `src/fitcv_cp/bq_store.py`
- Modify: BigQuery migration assets/scripts
- Modify: `tests/test_fitcv_cp/test_bq_store.py`

- [ ] **Step 1.1: Add run model fields**

Extend `PipelineRun` with nullable fields:

- `jobs_input_source`
- `jobs_input_json`
- `candidate_profile_source`
- `candidate_profile_json`

- [ ] **Step 1.2: Update BQ persistence helpers**

Update:

- `insert_run`
- `get_run`
- `_row_to_run`

to write/read the new fields.

- [ ] **Step 1.3: Add migration for `pipeline_runs`**

Add nullable columns:

- `jobs_input_source STRING`
- `jobs_input_json STRING`
- `candidate_profile_source STRING`
- `candidate_profile_json STRING`

- [ ] **Step 1.4: Add unit tests**

Cover:

- insert query includes new parameters
- read mapping includes new fields
- optional values round-trip correctly

- [ ] **Step 1.5: Verify**

Run:

```bash
/tmp/fitcv-test-env/bin/python -m pytest tests/test_fitcv_cp/test_bq_store.py -v
```

---

## Task 2: Make Rule Filter Results Run-Scoped

**Files:**

- Modify: `src/fitcv/rule_filter.py`
- Modify: `src/fitcv/pipeline.py`
- Modify: BigQuery migration assets/scripts
- Modify: `tests/test_rule_filter.py`
- Modify: `tests/test_pipeline.py`

> **Migration ordering note:** Apply the `rule_filter_results.run_id` migration before exercising the updated pipeline path against a real BigQuery instance. Once `store_filter_results(..., run_id, ...)` lands, inserts will fail if the live table does not yet have the new column.

- [ ] **Step 2.1: Add migration for `rule_filter_results.run_id`**

Add nullable column:

- `run_id STRING`

If the table is append-only, existing rows remain valid with `NULL`.

- [ ] **Step 2.2: Update `store_filter_results` signature**

Change to:

```python
store_filter_results(result: dict[str, list], run_id: str, config: dict[str, Any]) -> None
```

Persist `run_id` in both passed and rejected rows.

- [ ] **Step 2.3: Update pipeline call site**

In `run_pipeline`, pass `run_id` into `store_filter_results`.

- [ ] **Step 2.4: Add tests**

Cover:

- inserted rows include `run_id`
- pipeline passes `run_id` through

- [ ] **Step 2.5: Verify**

Run:

```bash
/tmp/fitcv-test-env/bin/python -m pytest tests/test_rule_filter.py tests/test_pipeline.py -v
```

---

## Task 3: Add Candidate Profile JSON Loader and Runtime Override

**Files:**

- Modify: `src/fitcv/candidate.py`
- Modify: `src/fitcv/pipeline.py`
- Modify: `tests/test_candidate.py`
- Modify: `tests/test_pipeline.py`

- [ ] **Step 3.1: Add `load_profile_json_text`**

Create helper:

```python
def load_profile_json_text(payload: str) -> dict[str, Any]:
```

Behavior:

- parse JSON
- require top-level object
- validate with existing `validate_profile()`
- required sections to cover in tests:
  - `experiences`
  - `skills`
  - `projects`
  - `achievements`
  - `preferences`
- raise clear error on invalid payload

- [ ] **Step 3.2: Update pipeline profile resolution**

Before loading YAML path, check:

```python
config.get("runtime_inputs", {}).get("candidate_profile_json")
```

If present:

- load via `load_profile_json_text`

Else:

- load via existing YAML path logic

- [ ] **Step 3.3: Add tests**

Cover:

- valid JSON profile loads
- invalid JSON fails
- missing required sections fail
- pipeline prefers runtime JSON override
- pipeline falls back to YAML path when absent

- [ ] **Step 3.4: Verify**

Run:

```bash
/tmp/fitcv-test-env/bin/python -m pytest tests/test_candidate.py tests/test_pipeline.py -v
```

---

## Task 4: Expand Admin Trigger Flow for Jobs and Candidate Inputs

**Files:**

- Modify: `src/fitcv_cp/app.py`
- Modify: `src/fitcv_cp/templates/runs_list.html`
- Modify: `tests/test_fitcv_cp/test_app.py`

- [ ] **Step 4.1: Extend form contract**

Add request fields:

- `jobs_input_mode`
- `jobs_text`
- `candidate_profile_mode`
- `candidate_profile_text`

Retain:

- `jobs_path`
- `jobs_file`
- `config_path`
- add `candidate_profile_file`

Clarification:

- the existing `jobs_path` input remains, but it becomes the input used when `jobs_input_mode=path`
- there is no separate legacy path-only flow after this change

- [ ] **Step 4.2: Implement explicit mode resolution**

Jobs modes:

- `path`
- `upload`
- `paste`

Candidate modes:

- `default_config`
- `upload`
- `paste`

The server must reject invalid combinations instead of guessing.

- [ ] **Step 4.3: Jobs input handling**

For `paste` mode:

- parse JSON
- require `list[object]`
- save canonical JSON to `data/uploads/{uuid}_pasted_jobs.json`
- store pretty JSON snapshot in run record
- set `jobs_path` to saved file path

For `upload` mode:

- save upload to `data/uploads`
- set `jobs_input_source=upload`

For `path` mode:

- use provided path
- set `jobs_input_source=path`

- [ ] **Step 4.4: Candidate profile input handling**

For `paste` mode:

- parse JSON object
- validate profile
- store canonical pretty JSON in run record
- set `candidate_profile_source=paste`

For `upload` mode:

- read file content
- parse and validate JSON object
- store canonical pretty JSON in run record
- set `candidate_profile_source=upload`

For `default_config` mode:

- no override payload
- set `candidate_profile_source=default_config`

- [ ] **Step 4.5: Inject runtime candidate override**

When a candidate profile snapshot exists:

- add `runtime_inputs.candidate_profile_json` to the effective config snapshot stored in the run

Handshake requirement:

- this value must be added to the in-memory `effective_config` before `insert_run(...)` and before enqueueing the worker
- `worker_job.py` must continue to rehydrate `effective_settings_json` from the stored run row and pass that config into `run_pipeline`
- `run_pipeline` then reads `config["runtime_inputs"]["candidate_profile_json"]` as the runtime override source

The stored run snapshot is therefore both audit state and the worker's runtime source of truth.

- [ ] **Step 4.6: Add tests**

Cover:

- jobs path success
- jobs upload success
- jobs paste success
- invalid jobs paste rejected
- candidate default success
- candidate upload success
- candidate paste success
- invalid candidate JSON rejected
- invalid candidate shape rejected
- inserted run contains correct source metadata and snapshots

- [ ] **Step 4.7: Verify**

Run:

```bash
/tmp/fitcv-test-env/bin/python -m pytest tests/test_fitcv_cp/test_app.py -v
```

---

## Task 5: Add Run-Scoped Filter Result Query

**Files:**

- Modify: `src/fitcv_cp/bq_store.py`
- Modify: `tests/test_fitcv_cp/test_bq_store.py`

- [ ] **Step 5.1: Add `list_filter_results_for_run`**

Add helper:

```python
def list_filter_results_for_run(
    run_id: str,
    bq: Any,
    *,
    project: str,
    dataset: str,
) -> list[dict[str, Any]]:
```

Query:

- `WHERE run_id = @run_id`
- ordered deterministically

- [ ] **Step 5.2: Add tests**

Cover:

- parameterized query
- correct table
- row dict conversion

- [ ] **Step 5.3: Verify**

Run:

```bash
/tmp/fitcv-test-env/bin/python -m pytest tests/test_fitcv_cp/test_bq_store.py -v
```

---

## Task 6: Render Reject Reasons and Run Inputs on Run Detail Page

**Files:**

- Modify: `src/fitcv_cp/app.py`
- Modify: `src/fitcv_cp/templates/run_detail.html`
- Modify: `tests/test_fitcv_cp/test_app.py`

- [ ] **Step 6.1: Extend run detail handler**

Fetch:

- run
- events
- CVs
- enriched jobs
- run-scoped filter results

Build:

- `filter_results_by_job_url`
- parsed candidate snapshot when available
- pretty JSON string for candidate snapshot
- jobs input source metadata and jobs JSON snapshot

- [ ] **Step 6.2: Candidate profile display**

Render:

- formatted readable section
- raw JSON `<pre><code>` section

For runs without `candidate_profile_json`:

- show fallback message:
  - “Used configured default candidate profile; run-scoped snapshot unavailable.”

- [ ] **Step 6.3: Filter outcomes display**

Render a filter-outcomes table or cards showing:

- title
- status
- reject reasons list

For jobs without a run-scoped filter result row:

- show “unavailable”

- [ ] **Step 6.4: Jobs input display**

Render:

- source type
- path if available
- raw JSON snapshot if present

For path/upload runs without snapshot:

- show path only

- [ ] **Step 6.5: Add tests**

Cover:

- reject reasons rendered
- candidate raw JSON rendered
- candidate formatted section rendered
- jobs input metadata rendered
- old-run fallback states render cleanly

- [ ] **Step 6.6: Verify**

Run:

```bash
/tmp/fitcv-test-env/bin/python -m pytest tests/test_fitcv_cp/test_app.py -v
```

---

## Task 7: Full Verification

- [ ] **Step 7.1: Run targeted suites**

```bash
/tmp/fitcv-test-env/bin/python -m pytest \
  tests/test_fitcv_cp/test_bq_store.py \
  tests/test_fitcv_cp/test_app.py \
  tests/test_rule_filter.py \
  tests/test_pipeline.py \
  tests/test_candidate.py -v
```

- [ ] **Step 7.2: Run broader regression suite if green**

```bash
/tmp/fitcv-test-env/bin/python -m pytest tests -q --tb=short
```

- [ ] **Step 7.3: Manual admin verification**

1. Start admin server
2. Trigger run with jobs path + default candidate profile
3. Trigger run with jobs upload + candidate upload
4. Trigger run with jobs paste + candidate paste
5. Inspect run detail pages

Expected:

- reject reasons visible
- candidate formatted view visible
- candidate raw JSON visible
- jobs input metadata visible
- old runs do not crash

---

## Important Implementation Notes

- Do not mutate repo-tracked YAML candidate profiles
- Do not infer reject reasons from summary counts
- Do not reuse non-run-scoped `rule_filter_results` rows for UI display
- Keep current YAML candidate profile fallback intact
- Keep pasted JSON canonicalized before persistence

---

## Acceptance Checklist

- [ ] `pipeline_runs` stores run-scoped input metadata and snapshots
- [ ] `rule_filter_results` stores `run_id`
- [ ] admin can trigger runs with pasted JSON for jobs and candidate profile
- [ ] run detail page shows reject reasons
- [ ] run detail page shows candidate profile raw and formatted views
- [ ] old runs render gracefully
- [ ] tests pass
