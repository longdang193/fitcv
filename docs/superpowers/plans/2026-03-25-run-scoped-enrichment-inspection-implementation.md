# Run-Scoped Enrichment Inspection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Persist immutable run-scoped enrichment outputs and expose them on the admin run detail page so admins can inspect what enrichment produced for a specific run.

**Architecture:** Keep `structured_jobs` as the latest-state table keyed by `job_url`, add a new append-only `run_structured_jobs` table keyed logically by `run_id + job_url`, write to both during the enrichment stage, and retrieve the run-scoped rows in the control plane for display alongside run results.

**Tech Stack:** Python, FastAPI, BigQuery, Jinja2, pytest

---

### File Map

**Backend pipeline**

- Create: `assets/bigquery/run_structured_jobs.sql`
- Create: `scripts/migrations/002_create_run_structured_jobs.py`
- Modify: `scripts/bootstrap_bigquery.py`
- Modify: `src/fitcv/enrich.py`
- Modify: `src/fitcv/pipeline.py`

**Control plane**

- Modify: `src/fitcv_cp/bq_store.py`
- Modify: `src/fitcv_cp/app.py`
- Modify: `src/fitcv_cp/templates/run_detail.html`

**Tests**

- Modify: `tests/test_enrich.py`
- Modify: `tests/test_pipeline.py`
- Modify: `tests/test_fitcv_cp/test_bq_store.py`
- Modify: `tests/test_fitcv_cp/test_app.py`

### Task 1: Define Run-Scoped Enrichment Storage

**Files:**

- Create: `assets/bigquery/run_structured_jobs.sql`
- Create: `scripts/migrations/002_create_run_structured_jobs.py`
- Modify: `scripts/bootstrap_bigquery.py`
- Test: none in this task

- [x] **Step 1.1: Add canonical DDL asset**

Create `assets/bigquery/run_structured_jobs.sql` with the run-scoped schema from the spec. Include `run_id`, `job_url`, core scraped fields, enriched fields, and `enriched_at`.

- [x] **Step 1.2: Wire bootstrap to create the table**

Update `scripts/bootstrap_bigquery.py` so the normal bootstrap path creates `run_structured_jobs` alongside the existing pipeline tables.

- [x] **Step 1.3: Add reproducible migration script**

Create `scripts/migrations/002_create_run_structured_jobs.py` to create the table for already-bootstrapped environments using the checked-in DDL asset.

- [x] **Step 1.4: Verify migration script can be invoked**

Table created successfully in BigQuery project `fitcv-491123`, dataset `fitcv` using direct DDL execution with template substitution.

- [x] **Step 1.5: Commit**

```bash
git add assets/bigquery/run_structured_jobs.sql scripts/bootstrap_bigquery.py scripts/migrations/002_create_run_structured_jobs.py
git commit -m "feat: add run-scoped enrichment storage"
```

### Task 2: Persist Run-Scoped Enrichment Rows

**Files:**

- Modify: `src/fitcv/enrich.py`
- Modify: `src/fitcv/pipeline.py`
- Modify: `tests/test_enrich.py`
- Modify: `tests/test_pipeline.py`

- [x] **Step 2.1: Write failing enrich persistence test**

Added unit tests in `tests/test_enrich.py` for `load_run_structured_jobs(...)`.

- [x] **Step 2.2: Run the test to verify failure**

Confirmed initial failure before implementation.

- [x] **Step 2.3: Implement run-scoped load helper**

In `src/fitcv/enrich.py`:

- Added `_RUN_SCHEMA_FIELDS`, `_RUN_SCHEMA_KEYS` constants
- Added `_map_to_run_structured_jobs_row()` helper
- Added `load_run_structured_jobs(enriched, run_id, config)` using `WRITE_APPEND`

- [x] **Step 2.4: Write failing pipeline test**

Added unit tests in `tests/test_pipeline.py` asserting both `load_structured_jobs` and `load_run_structured_jobs` are called.

- [x] **Step 2.5: Run the pipeline test to verify failure**

Confirmed initial failure.

- [x] **Step 2.6: Update pipeline to persist run-scoped rows**

In `src/fitcv/pipeline.py`: added `run_id` parameter and `load_run_structured_jobs(enriched, run_id, config)` call immediately after `load_structured_jobs`.

- [x] **Step 2.7: Run focused tests**

All enrich and pipeline tests pass (109/109 as of final verification).

- [x] **Step 2.8: Commit**

```bash
git commit -m "feat: persist run-scoped enriched jobs"
```

### Task 3: Add Control-Plane Retrieval

**Files:**

- Modify: `src/fitcv_cp/bq_store.py`
- Modify: `tests/test_fitcv_cp/test_bq_store.py`

- [x] **Step 3.1: Write failing store test**

Added `test_list_run_structured_jobs` in `tests/test_fitcv_cp/test_bq_store.py`.

- [x] **Step 3.2: Run the test to verify failure**

Confirmed failure before implementation.

- [x] **Step 3.3: Implement `list_run_structured_jobs(...)`**

In `src/fitcv_cp/bq_store.py`: parameterized `SELECT *` query ordered by `title, job_url`.

- [x] **Step 3.4: Run focused store tests**

All bq_store tests pass.

- [x] **Step 3.5: Commit**

```bash
git commit -m "feat: add run-scoped enrichment store access"
```

### Task 4: Render Enrichment Inspection on Run Detail

**Files:**

- Modify: `src/fitcv_cp/app.py`
- Modify: `src/fitcv_cp/templates/run_detail.html`
- Modify: `tests/test_fitcv_cp/test_app.py`

- [x] **Step 4.1: Write failing app/template tests**

Added 3 tests: renders section with rows, handles empty gracefully, renders required_skills.

- [x] **Step 4.2: Run the tests to verify failure**

Confirmed initial failures.

- [x] **Step 4.3: Update run detail route**

In `src/fitcv_cp/app.py`: `admin_run_detail` now calls `list_run_structured_jobs` and passes `enriched_jobs` to template.

- [x] **Step 4.4: Update run detail template**

Added `Enriched Jobs` table in `run_detail.html` showing: title (linked), location_type, seniority, job_family, domain, required_skills (top 5 + overflow count).

- [x] **Step 4.5: Run focused tests**

All app tests pass.

- [x] **Step 4.6: Commit**

```bash
git commit -m "feat: show run-scoped enrichment on run detail"
```

### Task 5: Optional Filter-Reason Merge

- [ ] **Step 5.1: Decide whether to merge filter reasons in this slice**

**Decision: deferred to follow-up feature.** The current Enriched Jobs table already shows the enrichment output. Filter reasons (pass/reject per job) are a separate concern and will be tracked in a dedicated follow-up plan.

### Task 6: Full Verification

**Files:**

- No code changes required unless failures are found

- [x] **Step 6.1: Run focused suites**

```
109 passed in 1.84s
```

All suites: `test_enrich.py`, `test_pipeline.py`, `test_fitcv_cp/test_bq_store.py`, `test_fitcv_cp/test_app.py` — all green.

- [x] **Step 6.2: Run broader control-plane regression suite**

109/109 pass — no regressions.

- [x] **Step 6.3: Manual verification**

- ✅ Run detail page shows Enriched Jobs section with real BigQuery data
- ✅ Fields match enrichment output (title, location_type, seniority, job_family, domain, required_skills)
- ✅ Empty enrichment rows render gracefully with "No enrichment data available"
- ✅ Section appears correctly for SUCCEEDED runs

- [x] **Step 6.4: Final commit or follow-up fixes**

Follow-up bugs found and fixed during verification (see Problems Log below).

## Notes

- Do not repurpose `structured_jobs` into a history table.
- Preserve current downstream behavior that expects latest-state `structured_jobs` keyed by `job_url`.
- Favor small, isolated commits per task to keep rollback and review simple.
