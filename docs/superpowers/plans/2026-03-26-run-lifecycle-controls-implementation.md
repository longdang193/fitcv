# Run Lifecycle Controls Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add persisted stop/cancel and archive/unarchive controls for pipeline runs, including queue-aware cancellation, archived-run list filtering, lifecycle audit events, and admin UI actions.

**Architecture:** Extend `pipeline_runs` with lifecycle metadata (`queue_job_id`, cancel-request fields, archive fields) and extend `RunStatus` with `cancelling` and `cancelled`. Use RQ job IDs to cancel claimable queued jobs, use cooperative checkpoint checks inside the worker for running jobs, append lifecycle events to `pipeline_run_events`, and expose the controls through FastAPI routes plus runs-list and run-detail UI actions.

**Tech Stack:** Python 3.11, FastAPI, Jinja2, RQ/Redis, BigQuery, pytest

---

## File Map

- **Modify:** `src/fitcv_cp/models.py`
  - Extend `RunStatus`
  - Add lifecycle metadata fields to `PipelineRun`
- **Modify:** `src/fitcv_cp/bq_store.py`
  - Persist and query lifecycle metadata
  - Add run lifecycle helper functions
- **Modify:** `src/fitcv_cp/queue.py`
  - Return/store RQ job id
  - Add queue-side cancel helper for queued jobs
- **Modify:** `src/fitcv_cp/worker_job.py`
  - Honor cancellation requests at safe checkpoints
  - Emit lifecycle events
- **Modify:** `src/fitcv/pipeline.py`
  - Add cooperative cancellation hook/checkpoint callback support
- **Modify:** `src/fitcv_cp/app.py`
  - Add stop/archive/unarchive endpoints
  - Add runs-list filter handling
  - Render lifecycle actions in admin pages
- **Modify:** `src/fitcv_cp/templates/runs_list.html`
  - Add lifecycle filters and row actions
- **Modify:** `src/fitcv_cp/templates/run_detail.html`
  - Add header lifecycle actions and archive visibility state
- **Modify:** `assets/bigquery/pipeline_runs.sql`
  - Add lifecycle columns for fresh bootstrap
- **Add:** `docs/superpowers/migrations/2026-03-26-pipeline_runs-add-lifecycle-columns.sql`
  - ALTER TABLE for existing datasets
- **Modify:** `tests/test_fitcv_cp/test_models.py`
- **Modify:** `tests/test_fitcv_cp/test_bq_store.py`
- **Modify:** `tests/test_fitcv_cp/test_queue.py`
- **Modify:** `tests/test_fitcv_cp/test_worker_job.py`
- **Modify:** `tests/test_fitcv_cp/test_app.py`

---

## Task 1: Extend lifecycle data model and BigQuery schema

**Files:**
- Modify: `src/fitcv_cp/models.py`
- Modify: `assets/bigquery/pipeline_runs.sql`
- Add: `docs/superpowers/migrations/2026-03-26-pipeline_runs-add-lifecycle-columns.sql`
- Test: `tests/test_fitcv_cp/test_models.py`

- [ ] **Step 1: Write failing model tests for new statuses and fields**

Add assertions for:
- `RunStatus.CANCELLING`
- `RunStatus.CANCELLED`
- `PipelineRun.queue_job_id`
- `PipelineRun.cancel_requested_at`
- `PipelineRun.cancel_requested_by`
- `PipelineRun.archived_at`
- `PipelineRun.archived_by`

Example:
```python
def test_run_status_values():
    assert set(RunStatus) == {
        RunStatus.QUEUED,
        RunStatus.RUNNING,
        RunStatus.CANCELLING,
        RunStatus.CANCELLED,
        RunStatus.SUCCEEDED,
        RunStatus.FAILED,
    }
```

- [ ] **Step 2: Run model tests to verify failure**

Run:
```bash
/tmp/fitcv-test-env/bin/pytest -q tests/test_fitcv_cp/test_models.py
```

Expected:
- FAIL because statuses and fields do not exist yet

- [ ] **Step 3: Update `RunStatus` and `PipelineRun` in `models.py`**

Add:
```python
class RunStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    CANCELLING = "cancelling"
    CANCELLED = "cancelled"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
```

Add nullable dataclass fields:
```python
queue_job_id: Optional[str] = None
cancel_requested_at: Optional[datetime.datetime] = None
cancel_requested_by: Optional[str] = None
archived_at: Optional[datetime.datetime] = None
archived_by: Optional[str] = None
```

- [ ] **Step 4: Update `pipeline_runs.sql` for fresh bootstrap**

Add columns to `assets/bigquery/pipeline_runs.sql`:
```sql
queue_job_id STRING OPTIONS(description="RQ job id for queued run cancellation"),
cancel_requested_at TIMESTAMP,
cancel_requested_by STRING,
archived_at TIMESTAMP,
archived_by STRING
```

- [ ] **Step 5: Add migration SQL for existing datasets**

Create `docs/superpowers/migrations/2026-03-26-pipeline_runs-add-lifecycle-columns.sql`:
```sql
ALTER TABLE `{project}.{dataset}.pipeline_runs`
ADD COLUMN IF NOT EXISTS queue_job_id STRING,
ADD COLUMN IF NOT EXISTS cancel_requested_at TIMESTAMP,
ADD COLUMN IF NOT EXISTS cancel_requested_by STRING,
ADD COLUMN IF NOT EXISTS archived_at TIMESTAMP,
ADD COLUMN IF NOT EXISTS archived_by STRING;
```

- [ ] **Step 6: Re-run model tests**

Run:
```bash
/tmp/fitcv-test-env/bin/pytest -q tests/test_fitcv_cp/test_models.py
```

Expected:
- PASS

- [ ] **Step 7: Commit**

```bash
git add src/fitcv_cp/models.py assets/bigquery/pipeline_runs.sql \
  docs/superpowers/migrations/2026-03-26-pipeline_runs-add-lifecycle-columns.sql \
  tests/test_fitcv_cp/test_models.py
git commit -m "feat(cp): add run lifecycle statuses and metadata"
```

---

## Task 2: Extend BigQuery store helpers for lifecycle operations

**Files:**
- Modify: `src/fitcv_cp/bq_store.py`
- Test: `tests/test_fitcv_cp/test_bq_store.py`

- [ ] **Step 1: Write failing BQ-store tests for lifecycle fields**

Add tests for:
- `insert_run()` includes `queue_job_id`
- `_row_to_run()` maps cancel/archive fields
- list query can exclude archived runs
- lifecycle update helpers use parameterized SQL

Example:
```python
def test_row_to_run_maps_lifecycle_fields():
    row = {
        "run_id": "r1",
        "status": "queued",
        "created_at": datetime.datetime.now(datetime.timezone.utc),
        "queue_job_id": "rq-job-1",
        "cancel_requested_at": None,
        "cancel_requested_by": None,
        "archived_at": None,
        "archived_by": None,
    }
    run = _row_to_run(row)
    assert run.queue_job_id == "rq-job-1"
```

- [ ] **Step 2: Run BQ-store tests to verify failure**

Run:
```bash
/tmp/fitcv-test-env/bin/pytest -q tests/test_fitcv_cp/test_bq_store.py
```

Expected:
- FAIL on missing lifecycle support

- [ ] **Step 3: Extend `insert_run()` and `_row_to_run()`**

Include all new lifecycle fields in insert/query mapping:
```python
"queue_job_id", "cancel_requested_at", "cancel_requested_by", "archived_at", "archived_by"
```

- [ ] **Step 4: Add focused lifecycle update helpers**

Add helpers such as:
```python
def update_run_queue_job_id(...): ...
def request_run_cancel(...): ...
def archive_run(...): ...
def unarchive_run(...): ...
```

Each helper must:
- use parameterized SQL
- update only the intended columns
- be small and single-purpose

- [ ] **Step 5: Add archived-filter support to `list_runs()`**

Recommended signature:
```python
def list_runs(..., limit: int = 50, include_archived: bool = False, archived_only: bool = False) -> list[PipelineRun]:
```

Use parameterized or fixed SQL variants:
- default: `WHERE archived_at IS NULL`
- archived-only: `WHERE archived_at IS NOT NULL`
- all: no archived filter

Deployment note:
- this code must not ship before the lifecycle-column migration is applied
- `list_runs()` will fail if `archived_at` does not yet exist in BigQuery

- [ ] **Step 6: Add lifecycle event helper if it simplifies app/worker code**

Optional helper:
```python
def append_lifecycle_event(run_id: str, stage: str, message: str, ...): ...
```

Use only if it reduces repetition cleanly; otherwise reuse `append_event()`.

- [ ] **Step 7: Re-run BQ-store tests**

Run:
```bash
/tmp/fitcv-test-env/bin/pytest -q tests/test_fitcv_cp/test_bq_store.py
```

Expected:
- PASS

- [ ] **Step 8: Commit**

```bash
git add src/fitcv_cp/bq_store.py tests/test_fitcv_cp/test_bq_store.py
git commit -m "feat(cp): add lifecycle persistence helpers"
```

---

## Task 3: Queue integration and cooperative cancellation

**Files:**
- Modify: `src/fitcv_cp/queue.py`
- Modify: `src/fitcv_cp/worker_job.py`
- Modify: `src/fitcv/pipeline.py`
- Test: `tests/test_fitcv_cp/test_queue.py`
- Test: `tests/test_fitcv_cp/test_worker_job.py`

- [ ] **Step 1: Write failing queue and worker tests**

Add tests for:
- `enqueue_run()` returns both `run_id` and queue job id, or exposes queue job id for persistence
- queued cancel removes or cancels the RQ job if still claimable
- worker exits early when cancellation already requested before heavy work
- worker marks `cancelling -> cancelled` and appends `run_cancelled`
- worker leaves terminal status authoritative if cancellation arrives too late

Example:
```python
def test_worker_marks_cancelled_when_cancel_requested_before_pipeline():
    ...
    assert updated_statuses == [RunStatus.RUNNING, RunStatus.CANCELLED]
```

- [ ] **Step 2: Run queue/worker tests to verify failure**

Run:
```bash
/tmp/fitcv-test-env/bin/pytest -q tests/test_fitcv_cp/test_queue.py tests/test_fitcv_cp/test_worker_job.py
```

Expected:
- FAIL on missing cancellation behavior

- [ ] **Step 3: Update `enqueue_run()` to capture the RQ job id**

Current code ignores the return value of `q.enqueue(...)`.
Do **not** change the existing `enqueue_run()` return type in isolation, because `app.py` currently expects a single `run_id`.

Add a new helper:
```python
def enqueue_run_with_job_id(...) -> tuple[str, str]:
    job = q.enqueue(...)
    return run_id, job.id
```

Keep `enqueue_run()` as a compatibility wrapper:
```python
def enqueue_run(...):
    run_id, _job_id = enqueue_run_with_job_id(...)
    return run_id
```

- [ ] **Step 4: Add queue-side cancel helper**

In `queue.py`, add:
```python
def cancel_queued_run(queue_job_id: str, redis_url: str = ...) -> bool:
    ...
```

Behavior:
- fetch job by id
- if it still exists and is cancelable, cancel/remove it
- return `True` if execution was successfully prevented
- return `False` if already claimed/missing

- [ ] **Step 5: Add cooperative cancellation checks in `worker_job.py`**

Define the worker order explicitly:

1. update run status to `RUNNING`
2. read the current run row
3. inspect `cancel_requested_at`
4. if cancellation is already requested, mark `cancelled`, append `run_cancelled`, exit early
5. otherwise continue with normal pipeline execution

Reuse the existing `get_run()` read in `worker_job.py` after the `RUNNING` update rather than adding a redundant extra BigQuery fetch.

During execution:
- pass a lightweight cancellation callback into `run_pipeline()` if supported
- after `run_pipeline()` returns, if the run was cancelled mid-flight but still completed, preserve terminal status

- [ ] **Step 6: Add checkpoint hook support in `pipeline.py`**

Minimal design:
```python
def run_pipeline(..., cancellation_check: Callable[[], bool] | None = None):
    ...
    if cancellation_check and cancellation_check():
        raise PipelineCancelled(...)
```

Check only at orchestrator-owned boundaries:
- before enrichment
- between enrichment batches
- before AI scoring
- between AI scoring batches
- before CV generation

Add a small internal exception, e.g.:
```python
class PipelineCancelled(Exception): ...
```

- [ ] **Step 7: Map cancellation exception to lifecycle status**

In `worker_job.py`:
- if pipeline raises cancellation exception, update `finished_at`
- mark status `cancelled`
- append `run_cancelled` event
- do not treat as `failed`

- [ ] **Step 8: Re-run queue/worker tests**

Run:
```bash
/tmp/fitcv-test-env/bin/pytest -q tests/test_fitcv_cp/test_queue.py tests/test_fitcv_cp/test_worker_job.py
```

Expected:
- PASS

- [ ] **Step 9: Commit**

```bash
git add src/fitcv_cp/queue.py src/fitcv_cp/worker_job.py src/fitcv/pipeline.py \
  tests/test_fitcv_cp/test_queue.py tests/test_fitcv_cp/test_worker_job.py
git commit -m "feat(cp): add queue cancellation and worker stop checkpoints"
```

---

## Task 4: Trigger path and lifecycle API routes

**Files:**
- Modify: `src/fitcv_cp/app.py`
- Test: `tests/test_fitcv_cp/test_app.py`

- [ ] **Step 1: Write failing app tests for stop/archive/unarchive/filter routes**

Add tests for:
- `POST /admin/runs/{run_id}/stop` on queued run -> JSON success for `fetch()` caller
- stop on succeeded run -> 409
- archive on succeeded run -> success
- archive on running run -> 409
- unarchive on archived run -> success
- `/admin/runs?view=archived` or `/admin/runs?filter=archived` passes archived-only query mode

Example:
```python
def test_admin_stop_queued_run_requests_cancel_and_returns_json():
    ...
    assert resp.status_code == 200
```

- [ ] **Step 2: Run app tests to verify failure**

Run:
```bash
/tmp/fitcv-test-env/bin/pytest -q tests/test_fitcv_cp/test_app.py
```

Expected:
- FAIL on missing routes and filter behavior

- [ ] **Step 3: Persist `queue_job_id` at trigger time**

Update both trigger paths in `app.py`:
- call `insert_run()` first as today
- call `enqueue_run_with_job_id()` and capture `queue_job_id`
- immediately persist `queue_job_id` via `update_run_queue_job_id()`

Preserve the existing “DB row first, enqueue second” contract.

- [ ] **Step 4: Add lifecycle action routes**

Add admin POST routes:
```python
@app.post("/admin/runs/{run_id}/stop")
@app.post("/admin/runs/{run_id}/archive")
@app.post("/admin/runs/{run_id}/unarchive")
```

These routes should return structured JSON responses for `fetch()` callers rather than redirect-only HTML responses.

Stop route behavior:
- load run
- validate eligible status
- if `queued` and `queue_job_id` still cancelable: cancel queue job, mark `cancelled`, append `cancel_requested` + `run_cancelled`
- else set `cancel_requested_at/by`, set `status=cancelling` if currently running, append `cancel_requested`

Archive route behavior:
- allow only `succeeded`, `failed`, `cancelled`
- set `archived_at/by`
- append `run_archived`

Unarchive route behavior:
- require archived run
- clear `archived_at/by`
- append `run_unarchived`

- [ ] **Step 5: Add runs-list filter handling**

Update `admin_runs()`:
```python
view = request.query_params.get("view", "active")
```

Map:
- `active` -> `include_archived=False`
- `all` -> `include_archived=True`
- `archived` -> `archived_only=True`

Pass current view into template context.

- [ ] **Step 6: Return proper conflicts instead of silent success**

For invalid repeated lifecycle actions:
- raise `HTTPException(status_code=409, detail="...")` for API routes
- for admin lifecycle UI actions, return structured JSON errors for `fetch()` callers so the page can show inline feedback and preserve current state

- [ ] **Step 7: Re-run app tests**

Run:
```bash
/tmp/fitcv-test-env/bin/pytest -q tests/test_fitcv_cp/test_app.py
```

Expected:
- PASS

- [ ] **Step 8: Commit**

```bash
git add src/fitcv_cp/app.py tests/test_fitcv_cp/test_app.py
git commit -m "feat(cp): add run lifecycle routes and list filters"
```

---

## Task 5: Admin UI for lifecycle controls

**Files:**
- Modify: `src/fitcv_cp/templates/runs_list.html`
- Modify: `src/fitcv_cp/templates/run_detail.html`
- Test: `tests/test_fitcv_cp/test_app.py`

- [ ] **Step 1: Write failing HTML assertions for lifecycle controls**

Add tests that assert:
- runs list shows `Active`, `All`, `Archived` filters
- queued/running rows show `Stop Run`
- terminal rows show `Archive`
- archived rows show `Unarchive`
- run detail header shows the correct lifecycle action for each state

- [ ] **Step 2: Run targeted HTML tests to verify failure**

Run:
```bash
/tmp/fitcv-test-env/bin/pytest -q tests/test_fitcv_cp/test_app.py -k "archive or stop or archived or filter"
```

Expected:
- FAIL on missing controls

- [ ] **Step 3: Update `runs_list.html`**

Add:
- top-of-page filter controls for `Active`, `All`, `Archived`
- per-row lifecycle action column
- `fetch()`-driven lifecycle action buttons using existing shared design-system classes

Suggested rules:
- `queued` / `running` -> `Stop Run`
- `succeeded` / `failed` / `cancelled` and not archived -> `Archive`
- archived rows -> `Unarchive`
- `cancelling` -> muted status, no archive button

- [ ] **Step 4: Update `run_detail.html`**

Add lifecycle actions to the header/meta action area:
- `Stop Run` for `queued`, `running`
- disabled informational state for `cancelling`
- `Archive Run` for eligible terminal, non-archived runs
- `Unarchive Run` for archived runs

Also show archive state metadata if archived:
```html
<span class="badge badge-warning">Archived</span>
```

- [ ] **Step 5: Surface lifecycle errors cleanly**

Use `fetch()` for lifecycle actions on both runs list and run detail.

If a lifecycle action fails with conflict or validation error:
- show a short inline error banner or status message in the current page
- do not reload the page
- do not clear current filter selection, active tab, or current page state

If a lifecycle action succeeds:
- update the action area optimistically if safe, or reload once after success
- preserve the current runs-list filter or active run-detail tab if a reload is used

- [ ] **Step 6: Re-run targeted HTML tests**

Run:
```bash
/tmp/fitcv-test-env/bin/pytest -q tests/test_fitcv_cp/test_app.py -k "archive or stop or archived or filter"
```

Expected:
- PASS

- [ ] **Step 7: Commit**

```bash
git add src/fitcv_cp/templates/runs_list.html src/fitcv_cp/templates/run_detail.html \
  tests/test_fitcv_cp/test_app.py
git commit -m "feat(cp): add lifecycle actions to admin UI"
```

---

## Task 6: Full verification and migration handoff

**Files:**
- No new product files
- Verify migration file and tests

- [ ] **Step 1: Run focused lifecycle test suite**

Run:
```bash
/tmp/fitcv-test-env/bin/pytest -q --tb=short \
  tests/test_fitcv_cp/test_models.py \
  tests/test_fitcv_cp/test_bq_store.py \
  tests/test_fitcv_cp/test_queue.py \
  tests/test_fitcv_cp/test_worker_job.py \
  tests/test_fitcv_cp/test_app.py
```

Expected:
- PASS

- [ ] **Step 2: Run broader non-integration suite**

Run:
```bash
/tmp/fitcv-test-env/bin/pytest -q --tb=short -m "not integration"
```

Expected:
- PASS

- [ ] **Step 3: Apply or hand off BigQuery migration**

Required migration file:
- `docs/superpowers/migrations/2026-03-26-pipeline_runs-add-lifecycle-columns.sql`

Confirm:
- fresh bootstrap DDL updated in `assets/bigquery/pipeline_runs.sql`
- existing dataset migration SQL is ready to apply

- [ ] **Step 4: Manual admin verification**

Check in browser:
- trigger a run and confirm queued row gets a stop button
- stop a queued run and confirm it becomes `cancelled`
- archive a terminal run and confirm it disappears from default view
- switch to `Archived` and confirm archived run remains readable
- open archived run detail and confirm `Unarchive Run` appears

- [ ] **Step 5: Migration sequencing check**

Before deploying code that queries lifecycle columns, confirm the migration has been applied to the live dataset.

Required deployment order:
1. apply `docs/superpowers/migrations/2026-03-26-pipeline_runs-add-lifecycle-columns.sql`
2. deploy lifecycle-control code

Do not deploy code that filters on `archived_at` or reads lifecycle metadata before the migration exists in BigQuery.

- [ ] **Step 6: Final commit**

```bash
git status --short
git add src/fitcv_cp/ src/fitcv/ assets/bigquery/ docs/superpowers/migrations/ tests/test_fitcv_cp/
git commit -m "feat(cp): add run lifecycle controls"
```

---

## Important Notes

- **Queue-aware queued stop requires `queue_job_id`.** Without persisting the RQ job id on the run row, queued cancellation will be unreliable and race-prone.
- **Do not break `enqueue_run()` mid-plan.** Add `enqueue_run_with_job_id()` first, then update callers to use it. Keep `enqueue_run()` as a compatibility wrapper.
- **Keep BigQuery as source of truth.** Trigger flow remains: insert run row first, enqueue second, then persist queue job id.
- **Migration must precede deploy.** `archived_at`, `archived_by`, `cancel_requested_at`, `cancel_requested_by`, and `queue_job_id` must exist in BigQuery before code that reads them is deployed.
- **Lifecycle events are required.** `cancel_requested`, `run_cancelled`, `run_archived`, and `run_unarchived` must appear in `pipeline_run_events`.
- **Archive is non-destructive.** Do not delete or mutate `pipeline_run_events`, `run_structured_jobs`, `rule_filter_results`, or snapshot JSON.
- **Conflict behavior is intentional.** Repeated invalid lifecycle actions return `409`, not silent success.
- **Cancellation checks stay coarse.** Only add checks at explicit orchestrator-owned boundaries; do not try to interrupt arbitrary in-flight external calls.
- **Use `fetch()` for lifecycle UI actions.** This is required to preserve current page state and show inline errors without full-page redirects.
