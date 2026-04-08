# Admin Run Inspection and Per-Run JSON Inputs — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add run-scoped filter inspection and per-run JSON input support so the admin UI can show reject reasons, inspect the candidate profile used for a run, and trigger runs with either file upload or pasted JSON for both jobs and candidate profile.

**Architecture:** Extend `pipeline_runs` with run-scoped input metadata and snapshots, make `rule_filter_results` run-scoped by adding `run_id`, support runtime candidate profile JSON override in the pipeline, and expand the admin UI and BQ helpers to render inspection data.

**Tech Stack:** Python, FastAPI, Jinja2, BigQuery, pytest

**Spec:** `docs/superpowers/specs/2026-03-26-admin-run-inspection-and-json-inputs-design.md`

---

## ✅ STATUS: COMPLETE — Deployed 2026-03-26

**Tests:** 372 pass, 7 skipped (integration)
**Commits:**
- `feat(admin-run-inspection): implement run-scoped input metadata and filter result inspection`
- `feat(ui): expand runs_list trigger form with jobs/candidate input mode tabs`

**BQ Migrations Applied:**
- `pipeline_runs` — 4 new columns added (run applied 2026-03-26)
- `rule_filter_results` — `run_id` column added (run applied 2026-03-26)

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

- [x] **Step 1.1: Add run model fields**

Extend `PipelineRun` with nullable fields:

- `jobs_input_source`
- `jobs_input_json`
- `candidate_profile_source`
- `candidate_profile_json`

- [x] **Step 1.2: Update BQ persistence helpers**

Update:

- `insert_run`
- `get_run`
- `_row_to_run`

to write/read the new fields.

- [x] **Step 1.3: Add migration for `pipeline_runs`**

Add nullable columns:

- `jobs_input_source STRING`
- `jobs_input_json STRING`
- `candidate_profile_source STRING`
- `candidate_profile_json STRING`

Migration file: `docs/superpowers/migrations/2026-03-26-pipeline_runs-add-input-metadata.sql`
**Applied live:** 2026-03-26 via `/tmp/run_migrations.py`

- [x] **Step 1.4: Add unit tests**

Cover:

- insert query includes new parameters
- read mapping includes new fields
- optional values round-trip correctly

- [x] **Step 1.5: Verify**

```
16 passed in 0.35s  (test_bq_store.py — 16 including 4 new Task 1 tests)
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

- [x] **Step 2.1: Add migration for `rule_filter_results.run_id`**

Migration file: `docs/superpowers/migrations/2026-03-26-rule_filter_results-add-run_id.sql`
**Applied live:** 2026-03-26 via `/tmp/run_migrations.py`

- [x] **Step 2.2: Update `store_filter_results` signature**

```python
store_filter_results(result: dict[str, list], run_id: str, config: dict[str, Any]) -> None
```

- [x] **Step 2.3: Update pipeline call site**

`store_filter_results(filter_result, run_id, config)`

- [x] **Step 2.4: Add tests**

2 new unit tests (google.cloud.bigquery.Client patch to capture rows).

- [x] **Step 2.5: Verify**

```
56 passed, 1 deselected  (test_rule_filter.py + test_pipeline.py)
```

---

## Task 3: Add Candidate Profile JSON Loader and Runtime Override

**Files:**

- Modify: `src/fitcv/candidate.py`
- Modify: `src/fitcv/pipeline.py`
- Modify: `tests/test_candidate.py`
- Modify: `tests/test_pipeline.py`

- [x] **Step 3.1: Add `load_profile_json_text`**

- [x] **Step 3.2: Update pipeline profile resolution**

```python
config.get("runtime_inputs", {}).get("candidate_profile_json")
```

- [x] **Step 3.3: Add tests** — 5 new tests in `test_candidate.py`

- [x] **Step 3.4: Verify**

```
21 passed, 1 deselected  (test_candidate.py)
```

---

## Task 4: Expand Admin Trigger Flow for Jobs and Candidate Inputs

**Files:**

- Modify: `src/fitcv_cp/app.py`
- Modify: `src/fitcv_cp/templates/runs_list.html`
- Modify: `tests/test_fitcv_cp/test_app.py`

- [x] **Step 4.1–4.5: Implement explicit mode resolution and runtime inject**

Jobs modes: `path` | `upload` | `paste`
Candidate modes: `default_config` | `upload` | `paste`
Added `_execute_trigger_with_inputs()` helper.

- [x] **Step 4.6: Added tests** — updated `test_admin_upload_trigger_success`

- [x] **Step 4.7: Verify** — `21 passed` (test_app.py)

---

## Task 5: Add Run-Scoped Filter Result Query

**Files:**

- Modify: `src/fitcv_cp/bq_store.py`
- Modify: `tests/test_fitcv_cp/test_bq_store.py`

- [x] **Step 5.1: Add `list_filter_results_for_run`** — parameterized `WHERE run_id = @run_id`

- [x] **Step 5.2–5.3: Tests + verify** — included in bq_store test suite

---

## Task 6: Render Reject Reasons and Run Inputs on Run Detail Page

**Files:**

- Modify: `src/fitcv_cp/app.py`
- Modify: `src/fitcv_cp/templates/run_detail.html`
- Modify: `tests/test_fitcv_cp/test_app.py`

- [x] **Step 6.1: Extend run detail handler** — fetches `filter_results`, builds `filter_results_by_job_url`, parses candidate profile JSON

- [x] **Step 6.2: Candidate profile display** — scrollable `<pre>` with source badge; hidden when not present

- [x] **Step 6.3: Filter outcomes display** — ✓ pass / ✗ reject badges with inline reason codes in Enriched Jobs table

- [x] **Step 6.4: Jobs input display** — Jobs Input Snapshot panel for paste-mode runs

- [x] **Step 6.5–6.6: Tests + verify** — `21 passed` (test_app.py)

---

## Task 7: Full Verification

- [x] **Step 7.1: Run targeted suites** — all pass
- [x] **Step 7.2: Run broader regression suite** — `372 passed, 7 deselected`
- [x] **Step 7.3: Manual admin verification** — trigger form update deployed and confirmed live

---

## Acceptance Checklist

- [x] `pipeline_runs` stores run-scoped input metadata and snapshots
- [x] `rule_filter_results` stores `run_id`
- [x] admin can trigger runs with pasted JSON for jobs and candidate profile
- [x] run detail page shows reject reasons
- [x] run detail page shows candidate profile raw and formatted views
- [x] old runs render gracefully
- [x] tests pass

---

## Post-Deploy Debug Log

### Issue 1 — Trigger form not updated (2026-03-26)

**Symptom:** The new jobs/candidate mode selectors were invisible in the UI. The old 3-field trigger form still appeared.

**Root cause:** Only the backend (`app.py`) was updated. The Jinja2 template `runs_list.html` was never modified — it still rendered the old `<form>` with `jobs_path`, `jobs_file`, `config_path` only.

**Fix:** Rewrote `runs_list.html` to expose the full tabbed trigger card with mode-switching JavaScript.

**Lesson:** When adding new form fields to a FastAPI endpoint, always update the corresponding HTML template in the same commit.

---

### Issue 2 — Internal Server Error on first trigger (2026-03-26)

**Symptom:** Trigger returned `500 Internal Server Error`. Web log showed:

```
BadRequest: 400 Column jobs_input_source is not present in table
fitcv-491123.fitcv.pipeline_runs at [5:13]
```

**Root cause:** The BigQuery migrations in `docs/superpowers/migrations/` were written but never applied to the live dataset. The `INSERT INTO pipeline_runs` statement now includes the 4 new columns which did not yet exist in BigQuery.

**Fix:** Ran `/tmp/run_migrations.py` to apply:
1. `ALTER TABLE pipeline_runs ADD COLUMN ...` (4 new columns)
2. `ALTER TABLE rule_filter_results ADD COLUMN run_id STRING`

**Lesson:** Schema-expanding migrations must be applied to the live BQ dataset before any code that writes to the new columns is deployed. "Migration note" alone in the plan is insufficient — add a pre-deploy checklist step.

---

### Issue 3 — Server unreachable after restart (2026-03-26)

**Symptom:** `start_admin_cp.sh` ran but browser showed "Unable to connect".

**Root cause:** GitHub Codespaces port forwarding stale — the browser tab was using an old forwarded URL that the Codespace no longer served after a server restart.

**Fix:** Re-open the forwarded URL from the **Ports** tab in VS Code. The server was always up (`ss -tlnp | grep 8000` confirmed the port was bound).

**Lesson:** In GitHub Codespaces, always re-open the preview from the Ports tab after any server restart rather than reusing the old browser tab.
