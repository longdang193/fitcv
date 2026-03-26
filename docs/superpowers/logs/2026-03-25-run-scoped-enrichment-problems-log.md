# Problems & Solutions Log — Run-Scoped Enrichment Inspection
**Date:** 2026-03-25  
**Feature:** Run-Scoped Enrichment Inspection (`feat/run-scoped-enrichment-inspection`)

---

## P1 — Mock server used instead of real server

**Problem:**  
The mock server (`mock_server.py`) was started to test the UI, but real GCP credentials and BigQuery access were available from the start. The mock wasted significant debugging time and caused confusion about whether data was real.

**Root Cause:**  
Credentials were not checked before choosing the testing strategy.

**Solution:**  
Deleted both `mock_server.py` files. Confirmed credentials in `.env.yaml` and `fitcv-491123-51c030d71e07.json`. Used `bash start_admin_cp.sh` for all subsequent testing.

**Prevention:**  
Always check `.env.yaml` for `service_account_key` and `gcp_project` before creating a mock server. If credentials exist, use the real server.

---

## P2 — `PipelineRun` has no `model_copy` (used Pydantic v2 API on a dataclass)

**Problem:**  
`mock_server.py` used `.model_copy(update={...})` to mutate run state, but `PipelineRun` is a `@dataclasses.dataclass`, not a Pydantic model. Error: `'PipelineRun' object has no attribute 'model_copy'`.

**Root Cause:**  
Assumed `PipelineRun` was a Pydantic model without checking `models.py`.

**Solution:**  
Replaced all `.model_copy(update={...})` calls with direct attribute assignment (e.g. `run.status = RunStatus.RUNNING`).

---

## P3 — Mock server still running after `start_admin_cp.sh`

**Problem:**  
`start_admin_cp.sh` kills `uvicorn fitcv_cp.main:app` but not `python mock_server.py`. The real server started but port 8000 was already occupied by the mock, so `start_admin_cp.sh` silently failed to bind or the mock kept handling requests.

**Root Cause:**  
The kill pattern in `start_admin_cp.sh` was too specific — it only matched the uvicorn process name.

**Solution:**  
Manually killed all relevant processes with `pkill -9 -f "mock_server\|uvicorn\|rq worker"` before starting the real server.

---

## P4 — Uvicorn `--reload` flag caused server crashes

**Problem:**  
`start_admin_cp.sh` started uvicorn with `--reload`. Each time a file changed (e.g. uploaded jobs written to `data/uploads/`), the reloader triggered a restart. Sometimes it failed to come back up, resulting in "Unable to connect to Server" errors mid-run.

**Root Cause:**  
`--reload` watches the filesystem for changes and restarts the server. File uploads triggered this.

**Solution:**  
Removed `--reload` from `start_admin_cp.sh`. Uvicorn now runs in stable production mode. Manual restart required when code changes.

---

## P5 — `No module named 'google.genai'`

**Problem:**  
Pipeline worker failed immediately with `ModuleNotFoundError: No module named 'google.genai'`.

**Root Cause:**  
`google-genai` was not installed in the `/tmp/fitcv-test-env` virtual environment used by the RQ worker.

**Solution:**  
```bash
uv pip install google-genai --python /tmp/fitcv-test-env
```

---

## P6 — `No module named 'vertexai'`

**Problem:**  
Pipeline progressed through enrichment but failed at vector search with `ModuleNotFoundError: No module named 'vertexai'`.

**Root Cause:**  
`vertexai` (part of `google-cloud-aiplatform`) was not installed in the venv.

**Solution:**  
```bash
uv pip install google-cloud-aiplatform --python /tmp/fitcv-test-env
```
Then verified all pipeline module imports succeed before restarting.

---

## P7 — `run_structured_jobs` BQ table missing (migration DDL uses template placeholders)

**Problem:**  
`scripts/migrations/002_create_run_structured_jobs.py` failed with  
`Error: DDL asset not found at /workspaces/fitcv/scripts/assets/bigquery/run_structured_jobs.sql`  
(wrong path). When called with the correct path, BQ returned:  
`400 Invalid project ID '{project}'` — the DDL uses `{project}` and `{dataset}` as literal placeholders.

**Root Cause:**  
The migration script had a wrong relative path for the DDL asset. The DDL itself used Python `str.format()`-style placeholders but the migration script didn't substitute them.

**Solution:**  
Created the table directly using substituted DDL:
```python
ddl = open('assets/bigquery/run_structured_jobs.sql').read()
ddl = ddl.replace('{project}', cfg['gcp_project']).replace('{dataset}', cfg['bigquery_dataset'])
bq.query(ddl).result()
```
**Follow-up:** Update the migration script to perform template substitution before execution.

---

## P8 — Feature branch not merged; server ran old code

**Problem:**  
The run detail page showed no Enriched Jobs section despite the pipeline running successfully. The server was running code from `feat/admin-control-plane` which did not yet include the enrichment inspection changes from `feat/run-scoped-enrichment-inspection`.

**Root Cause:**  
The feature was developed in a git worktree on a separate branch and never merged.

**Solution:**  
```bash
git stash
git merge feat/run-scoped-enrichment-inspection --no-edit
# resolved conflicts in pipeline.py (trivial docstring) and test_app.py (stash was empty)
git stash drop
```

---

## P9 — Merge conflict: `test_run_pipeline_uses_supplied_run_id` missing mock for `load_run_structured_jobs`

**Problem:**  
After merge, `tests/test_pipeline.py::test_run_pipeline_uses_supplied_run_id_for_summary_and_cv_records` failed with `KeyError: 'gcp_project'` because the test called the real `load_run_structured_jobs` instead of a mock.

**Root Cause:**  
The test had `@patch` decorators for all pipeline dependencies except the newly added `load_run_structured_jobs`. The stash pop brought in an earlier version of the test that predated the feature.

**Solution:**  
Added `@patch("fitcv.pipeline.load_run_structured_jobs")` and corresponding `mock_load_run_struct: MagicMock` parameter to the test function.

**Result:** 109/109 tests pass.

---

## P10 — Enrichment fields empty (`—`) for some jobs; wrong Gemini model

**Problem:**  
Some jobs (e.g. "Business Analyst", "Head of Analytics") showed `—` for ALL fields including `required_skills`. Also, setting `gemini_model: "gemini-2.0-flash"` caused a `404 NOT_FOUND` — that model is not available on this Vertex AI project.

**Root Cause:**  
`enrich_job` had no `gemini_model` key in `.env.yaml`, defaulting to `gemini-2.5-flash`. Some jobs returned unparseable responses (thinking tokens or extra text before JSON), causing `parse_extraction_response` to silently return `{}`. No warning was logged. The attempted fix of switching to `gemini-2.0-flash` made it worse — that model 404s on Vertex AI for this project.

**Solution:**  
1. Added `gemini_model: "gemini-2.5-flash"` and `ai_score_model: "gemini-2.5-flash"` to `.env.yaml` (explicit, verified working model)  
2. Added `WARNING` logging when `parse_extraction_response` returns errors so silent failures are visible in `rq_worker.log`:
   ```python
   if extraction["errors"]:
       logger.warning("Enrichment parse errors for job %r: %s", title, errors)
   ```

**Note:** The `—` for enum fields (`location_type`, `seniority`, `job_family`, `domain`) on other rows is **expected behavior** — the strict enum validator rejects values not in the allowed set. The empty `required_skills` is the silent parse-failure bug now surfaced by the warning log.

