# FitCV Admin Control Plane Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an internal admin UI + FastAPI backend + Redis worker that lets an admin trigger FitCV pipeline runs and inspect run status, history, and event logs without using the terminal.

**Architecture:** A new `src/fitcv_cp/` control-plane package wraps the existing `run_pipeline()` without modifying its business logic. FastAPI handles admin pages and a REST API; a Redis-backed RQ worker executes the pipeline in the background; two new BigQuery tables (`pipeline_runs`, `pipeline_run_events`) track lifecycle state. A single Dockerfile is shared by both the `web` and `worker` services, composed locally via `docker-compose.yml`.

**Tech Stack:** Python 3.11, FastAPI, Jinja2 (server-rendered templates), RQ + Redis (background jobs), `google-cloud-bigquery`, Docker + docker-compose.

---

## Task 1 — Data Models and BigQuery DDL

**Files:**
- Create: `src/fitcv_cp/__init__.py`
- Create: `src/fitcv_cp/models.py`
- Create: `assets/bigquery/pipeline_runs.sql`
- Create: `assets/bigquery/pipeline_run_events.sql`
- Create: `tests/fitcv_cp/__init__.py`
- Create: `tests/fitcv_cp/test_models.py`

- [ ] **Step 1.1: Write the failing model tests**

```python
# tests/fitcv_cp/test_models.py
from fitcv_cp.models import RunStatus, PipelineRun, RunEvent
import dataclasses

def test_run_status_values():
    assert set(RunStatus) == {RunStatus.QUEUED, RunStatus.RUNNING, RunStatus.SUCCEEDED, RunStatus.FAILED}

def test_pipeline_run_fields():
    fields = {f.name for f in dataclasses.fields(PipelineRun)}
    assert {"run_id", "status", "triggered_by", "trigger_source", "jobs_path",
            "config_path", "created_at"} <= fields

def test_run_event_fields():
    fields = {f.name for f in dataclasses.fields(RunEvent)}
    assert {"run_id", "event_id", "stage", "level", "message", "created_at"} <= fields
```

- [ ] **Step 1.2: Run to confirm failure**

```bash
pytest tests/fitcv_cp/test_models.py -v
# Expected: ImportError — fitcv_cp not found
```

- [ ] **Step 1.3: Create the package and models**

```python
# src/fitcv_cp/__init__.py
# (empty)
```

```python
# src/fitcv_cp/models.py
import dataclasses, datetime
from enum import Enum
from typing import Optional

class RunStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"

@dataclasses.dataclass
class PipelineRun:
    run_id: str
    status: RunStatus
    triggered_by: str
    trigger_source: str
    jobs_path: str
    config_path: str
    created_at: datetime.datetime
    started_at: Optional[datetime.datetime] = None
    finished_at: Optional[datetime.datetime] = None
    total_jobs: Optional[int] = None
    passed_filter: Optional[int] = None
    ranked: Optional[int] = None
    cvs_generated: Optional[int] = None
    error_message: Optional[str] = None

@dataclasses.dataclass
class RunEvent:
    run_id: str
    event_id: str
    stage: str
    level: str
    message: str
    created_at: datetime.datetime
    payload_json: Optional[str] = None
```

- [ ] **Step 1.4: Write the BigQuery DDL files**

`assets/bigquery/pipeline_runs.sql`:
```sql
CREATE TABLE IF NOT EXISTS `{project}.{dataset}.pipeline_runs` (
  run_id          STRING    NOT NULL OPTIONS(description="UUID4 run identifier"),
  status          STRING    NOT NULL OPTIONS(description="queued | running | succeeded | failed"),
  triggered_by    STRING,
  trigger_source  STRING,
  jobs_path       STRING,
  config_path     STRING,
  created_at      TIMESTAMP NOT NULL,
  started_at      TIMESTAMP,
  finished_at     TIMESTAMP,
  total_jobs      INT64,
  passed_filter   INT64,
  ranked          INT64,
  cvs_generated   INT64,
  error_message   STRING
);
```

`assets/bigquery/pipeline_run_events.sql`:
```sql
CREATE TABLE IF NOT EXISTS `{project}.{dataset}.pipeline_run_events` (
  run_id       STRING    NOT NULL OPTIONS(description="FK -> pipeline_runs.run_id"),
  event_id     STRING    NOT NULL OPTIONS(description="UUID4 event identifier"),
  stage        STRING    NOT NULL,
  level        STRING    NOT NULL OPTIONS(description="info | warning | error"),
  message      STRING    NOT NULL,
  payload_json STRING,
  created_at   TIMESTAMP NOT NULL
);
```

- [ ] **Step 1.5: Run tests to confirm they pass**

```bash
pytest tests/fitcv_cp/test_models.py -v
# Expected: 3 passed
```

- [ ] **Step 1.6: Commit**

```bash
git add src/fitcv_cp/ tests/fitcv_cp/ assets/bigquery/pipeline_runs.sql assets/bigquery/pipeline_run_events.sql
git commit -m "feat(cp): add control-plane data models and BigQuery DDL"
```

---

## Task 2 — BigQuery Store

**Files:**
- Create: `src/fitcv_cp/bq_store.py`
- Create: `tests/fitcv_cp/test_bq_store.py`

- [ ] **Step 2.1: Write failing tests**

```python
# tests/fitcv_cp/test_bq_store.py
from unittest.mock import MagicMock
from fitcv_cp.bq_store import insert_run, update_run_status, append_event, get_run, list_runs, get_events
from fitcv_cp.models import PipelineRun, RunEvent, RunStatus
import datetime, uuid

def _make_run() -> PipelineRun:
    return PipelineRun(
        run_id=str(uuid.uuid4()), status=RunStatus.QUEUED, triggered_by="admin",
        trigger_source="ui", jobs_path="data/sample_jobs.json",
        config_path=".env.yaml", created_at=datetime.datetime.utcnow(),
    )

def test_insert_run_calls_bq():
    bq = MagicMock()
    insert_run(_make_run(), bq, project="p", dataset="d")
    bq.insert_rows_json.assert_called_once()

def test_update_run_status_calls_query():
    bq = MagicMock()
    update_run_status("rid", RunStatus.RUNNING, bq, project="p", dataset="d")
    bq.query.assert_called_once()

def test_append_event_calls_bq():
    bq = MagicMock()
    ev = RunEvent(run_id="rid", event_id=str(uuid.uuid4()), stage="ingest",
                  level="info", message="done", created_at=datetime.datetime.utcnow())
    append_event(ev, bq, project="p", dataset="d")
    bq.insert_rows_json.assert_called_once()

def test_get_run_returns_none_when_not_found():
    bq = MagicMock()
    bq.query.return_value.result.return_value = iter([])
    assert get_run("missing", bq, project="p", dataset="d") is None

def test_list_runs_returns_list():
    bq = MagicMock()
    bq.query.return_value.result.return_value = iter([])
    assert isinstance(list_runs(bq, project="p", dataset="d"), list)

def test_get_events_returns_list():
    bq = MagicMock()
    bq.query.return_value.result.return_value = iter([])
    assert isinstance(get_events("rid", bq, project="p", dataset="d"), list)
```

- [ ] **Step 2.2: Run to confirm failure**

```bash
pytest tests/fitcv_cp/test_bq_store.py -v
# Expected: ImportError
```

- [ ] **Step 2.3: Implement `bq_store.py`**

```python
# src/fitcv_cp/bq_store.py
"""BigQuery persistence helpers for control-plane tables."""
import datetime, json, logging
from typing import Any, Optional
from fitcv_cp.models import PipelineRun, RunEvent, RunStatus

logger = logging.getLogger(__name__)

def insert_run(run: PipelineRun, bq: Any, *, project: str, dataset: str) -> None:
    table = f"{project}.{dataset}.pipeline_runs"
    row = {"run_id": run.run_id, "status": run.status.value,
           "triggered_by": run.triggered_by, "trigger_source": run.trigger_source,
           "jobs_path": run.jobs_path, "config_path": run.config_path,
           "created_at": run.created_at.isoformat()}
    errors = bq.insert_rows_json(table, [row])
    if errors:
        logger.error("BQ insert_run errors: %s", errors)

def update_run_status(run_id: str, status: RunStatus, bq: Any, *, project: str, dataset: str,
                      started_at: Optional[datetime.datetime] = None,
                      finished_at: Optional[datetime.datetime] = None,
                      summary: Optional[dict] = None,
                      error_message: Optional[str] = None) -> None:
    sets = [f"status = '{status.value}'"]
    if started_at:
        sets.append(f"started_at = TIMESTAMP('{started_at.isoformat()}')")
    if finished_at:
        sets.append(f"finished_at = TIMESTAMP('{finished_at.isoformat()}')")
    if summary:
        for k in ["total_jobs", "passed_filter", "ranked", "cvs_generated"]:
            if k in summary:
                sets.append(f"{k} = {int(summary[k])}")
    if error_message:
        safe = error_message.replace("'", "\\'")
        sets.append(f"error_message = '{safe}'")
    sql = (f"UPDATE `{project}.{dataset}.pipeline_runs` "
           f"SET {', '.join(sets)} WHERE run_id = '{run_id}'")
    bq.query(sql).result()

def append_event(event: RunEvent, bq: Any, *, project: str, dataset: str) -> None:
    table = f"{project}.{dataset}.pipeline_run_events"
    row = {"run_id": event.run_id, "event_id": event.event_id, "stage": event.stage,
           "level": event.level, "message": event.message,
           "payload_json": event.payload_json, "created_at": event.created_at.isoformat()}
    errors = bq.insert_rows_json(table, [row])
    if errors:
        logger.warning("BQ append_event errors: %s", errors)

def get_run(run_id: str, bq: Any, *, project: str, dataset: str) -> Optional[PipelineRun]:
    sql = f"SELECT * FROM `{project}.{dataset}.pipeline_runs` WHERE run_id = '{run_id}' LIMIT 1"
    rows = list(bq.query(sql).result())
    return _row_to_run(rows[0]) if rows else None

def list_runs(bq: Any, *, project: str, dataset: str, limit: int = 50) -> list[PipelineRun]:
    sql = f"SELECT * FROM `{project}.{dataset}.pipeline_runs` ORDER BY created_at DESC LIMIT {limit}"
    return [_row_to_run(r) for r in bq.query(sql).result()]

def get_events(run_id: str, bq: Any, *, project: str, dataset: str) -> list[RunEvent]:
    sql = (f"SELECT * FROM `{project}.{dataset}.pipeline_run_events` "
           f"WHERE run_id = '{run_id}' ORDER BY created_at ASC")
    return [_row_to_event(r) for r in bq.query(sql).result()]

def _row_to_run(row: Any) -> PipelineRun:
    r = dict(row)
    return PipelineRun(run_id=r["run_id"], status=RunStatus(r["status"]),
                       triggered_by=r.get("triggered_by") or "",
                       trigger_source=r.get("trigger_source") or "",
                       jobs_path=r.get("jobs_path") or "",
                       config_path=r.get("config_path") or "",
                       created_at=r["created_at"], started_at=r.get("started_at"),
                       finished_at=r.get("finished_at"), total_jobs=r.get("total_jobs"),
                       passed_filter=r.get("passed_filter"), ranked=r.get("ranked"),
                       cvs_generated=r.get("cvs_generated"), error_message=r.get("error_message"))

def _row_to_event(row: Any) -> RunEvent:
    r = dict(row)
    return RunEvent(run_id=r["run_id"], event_id=r["event_id"], stage=r["stage"],
                    level=r["level"], message=r["message"], created_at=r["created_at"],
                    payload_json=r.get("payload_json"))
```

- [ ] **Step 2.4: Run tests**

```bash
pytest tests/fitcv_cp/test_bq_store.py -v
# Expected: 6 passed
```

- [ ] **Step 2.5: Commit**

```bash
git add src/fitcv_cp/bq_store.py tests/fitcv_cp/test_bq_store.py
git commit -m "feat(cp): add BigQuery store for pipeline_runs and pipeline_run_events"
```

---

## Task 3 — Pipeline Reporter Integration

**Files:**
- Create: `src/fitcv_cp/reporter.py`
- Modify: `src/fitcv/pipeline.py` (add optional `reporter` kwarg + emit calls)
- Create: `tests/fitcv_cp/test_reporter.py`

- [ ] **Step 3.1: Write failing reporter tests**

```python
# tests/fitcv_cp/test_reporter.py
from unittest.mock import MagicMock
from fitcv_cp.reporter import PipelineReporter

def test_reporter_emits_event():
    bq = MagicMock()
    reporter = PipelineReporter(run_id="r1", bq=bq, project="p", dataset="d")
    reporter.emit("ingest", "info", "Layer 1 complete")
    bq.insert_rows_json.assert_called_once()

def test_reporter_noop_without_bq():
    reporter = PipelineReporter(run_id="r1", bq=None, project="p", dataset="d")
    reporter.emit("ingest", "info", "ok")  # must not raise

def test_reporter_payload_serialized():
    bq = MagicMock()
    reporter = PipelineReporter(run_id="r1", bq=bq, project="p", dataset="d")
    reporter.emit("enrich", "error", "timeout", payload={"retries": 3})
    call_args = bq.insert_rows_json.call_args[0][1][0]
    assert call_args["level"] == "error"
    assert "retries" in call_args["payload_json"]
```

- [ ] **Step 3.2: Run to confirm failure**

```bash
pytest tests/fitcv_cp/test_reporter.py -v
# Expected: ImportError
```

- [ ] **Step 3.3: Implement `reporter.py`**

```python
# src/fitcv_cp/reporter.py
"""Lightweight event reporter injected into run_pipeline() by the worker."""
import datetime, json, logging, uuid
from typing import Any, Optional
from fitcv_cp.bq_store import append_event
from fitcv_cp.models import RunEvent

logger = logging.getLogger(__name__)

class PipelineReporter:
    def __init__(self, run_id: str, bq: Any, *, project: str, dataset: str) -> None:
        self._run_id = run_id
        self._bq = bq
        self._project = project
        self._dataset = dataset

    def emit(self, stage: str, level: str, message: str,
             payload: Optional[dict[str, Any]] = None) -> None:
        if self._bq is None:
            return
        event = RunEvent(
            run_id=self._run_id, event_id=str(uuid.uuid4()), stage=stage,
            level=level, message=message, created_at=datetime.datetime.utcnow(),
            payload_json=json.dumps(payload) if payload else None,
        )
        try:
            append_event(event, self._bq, project=self._project, dataset=self._dataset)
        except Exception as exc:
            logger.warning("Reporter failed to write event: %s", exc)
```

- [ ] **Step 3.4: Add `reporter` kwarg to `run_pipeline()` in `src/fitcv/pipeline.py`**

Change signature:
```python
def run_pipeline(
    jobs_path: str,
    config_path: str = ".env.yaml",
    reporter: object = None,   # Optional[PipelineReporter] — avoids circular import
) -> dict[str, Any]:
```

Add these emit calls at stage boundaries (after each layer):
```python
# After load_structured_jobs():
if reporter is not None:
    reporter.emit("layer1_jobs", "info", f"Ingested {len(raw_jobs)} jobs, enriched {len(enriched)}")  # type: ignore[union-attr]

# After load_candidate_to_bigquery():
if reporter is not None:
    reporter.emit("layer2_candidate", "info", "Candidate profile loaded")  # type: ignore[union-attr]

# After store_filter_results():
if reporter is not None:
    reporter.emit("layer3_filter", "info", f"{len(passed_jobs)} passed rule filter")  # type: ignore[union-attr]

# After store_final_ranking():
if reporter is not None:
    reporter.emit("layer3_ranking", "info", f"Final ranking: top {len(ranked)} jobs")  # type: ignore[union-attr]

# Just before return summary:
if reporter is not None:
    reporter.emit("pipeline_complete", "info", str(summary))  # type: ignore[union-attr]
```

- [ ] **Step 3.5: Run reporter tests and existing pipeline tests**

```bash
pytest tests/fitcv_cp/test_reporter.py tests/test_pipeline.py -v
# Expected: all pass
```

- [ ] **Step 3.6: Commit**

```bash
git add src/fitcv_cp/reporter.py tests/fitcv_cp/test_reporter.py src/fitcv/pipeline.py
git commit -m "feat(cp): add PipelineReporter; wire optional reporter into run_pipeline()"
```

---

## Task 4 — Redis Queue and Worker Job

**Files:**
- Create: `src/fitcv_cp/queue.py`
- Create: `src/fitcv_cp/worker_job.py`
- Create: `tests/fitcv_cp/test_queue.py`
- Create: `tests/fitcv_cp/test_worker_job.py`

- [ ] **Step 4.1: Write failing queue tests**

```python
# tests/fitcv_cp/test_queue.py
from unittest.mock import MagicMock, patch
from fitcv_cp.queue import enqueue_run

def test_enqueue_run_returns_uuid():
    mock_q = MagicMock()
    with patch("fitcv_cp.queue.get_queue", return_value=mock_q):
        run_id = enqueue_run(jobs_path="data/sample_jobs.json",
                             config_path=".env.yaml", triggered_by="admin")
    assert isinstance(run_id, str) and len(run_id) == 36
    mock_q.enqueue.assert_called_once()
```

- [ ] **Step 4.2: Write failing worker tests**

```python
# tests/fitcv_cp/test_worker_job.py
from unittest.mock import MagicMock, patch
from fitcv_cp.worker_job import execute_pipeline_run

def test_worker_marks_succeeded_on_success():
    bq = MagicMock()
    bq.query.return_value.result.return_value = iter([])
    with patch("fitcv_cp.worker_job.run_pipeline", return_value={
        "run_id": "r1", "total_jobs": 5, "passed_filter": 3, "ranked": 2, "cvs_generated": 1
    }), patch("fitcv_cp.worker_job._get_bq", return_value=bq):
        execute_pipeline_run(run_id="r1", jobs_path="data/sample_jobs.json",
                             config_path=".env.yaml")
    assert bq.query.call_count >= 2  # running + succeeded

def test_worker_marks_failed_on_exception():
    bq = MagicMock()
    bq.query.return_value.result.return_value = iter([])
    with patch("fitcv_cp.worker_job.run_pipeline", side_effect=RuntimeError("boom")), \
         patch("fitcv_cp.worker_job._get_bq", return_value=bq):
        execute_pipeline_run(run_id="r1", jobs_path="data/sample_jobs.json",
                             config_path=".env.yaml")
    last_sql = bq.query.call_args_list[-1][0][0]
    assert "failed" in last_sql
```

- [ ] **Step 4.3: Run to confirm failure**

```bash
pytest tests/fitcv_cp/test_queue.py tests/fitcv_cp/test_worker_job.py -v
# Expected: ImportError
```

- [ ] **Step 4.4: Implement `queue.py`**

```python
# src/fitcv_cp/queue.py
"""RQ queue setup for background pipeline execution."""
import uuid
from typing import Optional
import redis
from rq import Queue
from fitcv_cp import worker_job  # noqa: F401

_queue: Optional[Queue] = None

def get_queue(redis_url: str = "redis://redis:6379/0") -> Queue:
    global _queue
    if _queue is None:
        conn = redis.from_url(redis_url)
        _queue = Queue("fitcv", connection=conn)
    return _queue

def enqueue_run(jobs_path: str, config_path: str, triggered_by: str,
                redis_url: str = "redis://redis:6379/0") -> str:
    run_id = str(uuid.uuid4())
    q = get_queue(redis_url)
    q.enqueue(worker_job.execute_pipeline_run, run_id=run_id,
              jobs_path=jobs_path, config_path=config_path, job_timeout=3600)
    return run_id
```

- [ ] **Step 4.5: Implement `worker_job.py`**

```python
# src/fitcv_cp/worker_job.py
"""RQ job: execute one pipeline run and persist lifecycle state."""
import datetime, logging, os
from google.cloud import bigquery
from fitcv.pipeline import run_pipeline
from fitcv_cp.bq_store import update_run_status
from fitcv_cp.models import RunStatus
from fitcv_cp.reporter import PipelineReporter

logger = logging.getLogger(__name__)

def _get_bq() -> bigquery.Client:
    return bigquery.Client()

def execute_pipeline_run(run_id: str, jobs_path: str, config_path: str) -> None:
    project = os.environ.get("GCP_PROJECT", "")
    dataset = os.environ.get("BIGQUERY_DATASET", "fitcv")
    bq = _get_bq()
    try:
        update_run_status(run_id, RunStatus.RUNNING, bq, project=project, dataset=dataset,
                          started_at=datetime.datetime.utcnow())
        reporter = PipelineReporter(run_id=run_id, bq=bq, project=project, dataset=dataset)
        summary = run_pipeline(jobs_path=jobs_path, config_path=config_path, reporter=reporter)
        update_run_status(run_id, RunStatus.SUCCEEDED, bq, project=project, dataset=dataset,
                          finished_at=datetime.datetime.utcnow(), summary=summary)
    except Exception as exc:
        logger.error("[run_id=%s] Pipeline failed: %s", run_id, exc)
        update_run_status(run_id, RunStatus.FAILED, bq, project=project, dataset=dataset,
                          finished_at=datetime.datetime.utcnow(), error_message=str(exc))
```

- [ ] **Step 4.6: Run tests**

```bash
pytest tests/fitcv_cp/test_queue.py tests/fitcv_cp/test_worker_job.py -v
# Expected: all pass
```

- [ ] **Step 4.7: Commit**

```bash
git add src/fitcv_cp/queue.py src/fitcv_cp/worker_job.py tests/fitcv_cp/test_queue.py tests/fitcv_cp/test_worker_job.py
git commit -m "feat(cp): add Redis/RQ queue and worker job"
```

---

## Task 5 — FastAPI App and Admin UI

**Files:**
- Create: `src/fitcv_cp/app.py`
- Create: `src/fitcv_cp/templates/base.html`
- Create: `src/fitcv_cp/templates/runs_list.html`
- Create: `src/fitcv_cp/templates/run_detail.html`
- Create: `tests/fitcv_cp/test_app.py`

- [ ] **Step 5.1: Write failing API tests**

```python
# tests/fitcv_cp/test_app.py
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from fitcv_cp.app import create_app

def _app():
    bq = MagicMock()
    return create_app(bq=bq, project="p", dataset="d", redis_url="redis://localhost:6379/0")

def test_post_runs_returns_201():
    with patch("fitcv_cp.app.enqueue_run", return_value="run-123"), \
         patch("fitcv_cp.app.insert_run"):
        resp = TestClient(_app()).post("/runs", json={"jobs_path": "data/sample_jobs.json"})
    assert resp.status_code == 201
    assert "run_id" in resp.json()

def test_get_runs_returns_list():
    with patch("fitcv_cp.app.list_runs", return_value=[]):
        resp = TestClient(_app()).get("/runs")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)

def test_get_run_detail_not_found():
    with patch("fitcv_cp.app.get_run", return_value=None):
        resp = TestClient(_app()).get("/runs/missing-id")
    assert resp.status_code == 404

def test_get_run_events():
    with patch("fitcv_cp.app.get_run", return_value=MagicMock()), \
         patch("fitcv_cp.app.get_events", return_value=[]):
        resp = TestClient(_app()).get("/runs/some-id/events")
    assert resp.status_code == 200
```

- [ ] **Step 5.2: Run to confirm failure**

```bash
pytest tests/fitcv_cp/test_app.py -v
# Expected: ImportError
```

- [ ] **Step 5.3: Implement `app.py`**

```python
# src/fitcv_cp/app.py
"""FastAPI admin control plane app."""
import datetime
from pathlib import Path
from typing import Any
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from fitcv_cp.bq_store import get_events, get_run, insert_run, list_runs
from fitcv_cp.models import PipelineRun, RunStatus
from fitcv_cp.queue import enqueue_run

TEMPLATES_DIR = Path(__file__).parent / "templates"

class TriggerRequest(BaseModel):
    jobs_path: str = "data/sample_jobs.json"
    config_path: str = ".env.yaml"
    triggered_by: str = "admin"

def create_app(bq: Any, project: str, dataset: str, redis_url: str) -> FastAPI:
    app = FastAPI(title="FitCV Admin Control Plane")
    templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

    @app.post("/runs", status_code=201)
    def trigger_run(req: TriggerRequest) -> dict:
        run_id = enqueue_run(jobs_path=req.jobs_path, config_path=req.config_path,
                              triggered_by=req.triggered_by, redis_url=redis_url)
        run = PipelineRun(run_id=run_id, status=RunStatus.QUEUED, triggered_by=req.triggered_by,
                          trigger_source="ui", jobs_path=req.jobs_path, config_path=req.config_path,
                          created_at=datetime.datetime.utcnow())
        insert_run(run, bq, project=project, dataset=dataset)
        return {"run_id": run_id}

    @app.get("/runs")
    def get_runs() -> list:
        return [_run_to_dict(r) for r in list_runs(bq, project=project, dataset=dataset)]

    @app.get("/runs/{run_id}")
    def get_run_detail(run_id: str) -> dict:
        run = get_run(run_id, bq, project=project, dataset=dataset)
        if run is None:
            raise HTTPException(status_code=404, detail="Run not found")
        return _run_to_dict(run)

    @app.get("/runs/{run_id}/events")
    def get_run_events(run_id: str) -> list:
        run = get_run(run_id, bq, project=project, dataset=dataset)
        if run is None:
            raise HTTPException(status_code=404, detail="Run not found")
        events = get_events(run_id, bq, project=project, dataset=dataset)
        return [{"event_id": e.event_id, "stage": e.stage, "level": e.level,
                 "message": e.message, "created_at": e.created_at.isoformat()} for e in events]

    @app.get("/admin/runs", response_class=HTMLResponse)
    def admin_runs(request: Request) -> HTMLResponse:
        runs = list_runs(bq, project=project, dataset=dataset)
        return templates.TemplateResponse("runs_list.html", {"request": request, "runs": runs})

    @app.get("/admin/runs/{run_id}", response_class=HTMLResponse)
    def admin_run_detail(request: Request, run_id: str) -> HTMLResponse:
        run = get_run(run_id, bq, project=project, dataset=dataset)
        if run is None:
            raise HTTPException(status_code=404)
        events = get_events(run_id, bq, project=project, dataset=dataset)
        return templates.TemplateResponse("run_detail.html",
                                          {"request": request, "run": run, "events": events})

    return app

def _run_to_dict(run: PipelineRun) -> dict:
    return {"run_id": run.run_id, "status": run.status.value, "triggered_by": run.triggered_by,
            "jobs_path": run.jobs_path, "created_at": run.created_at.isoformat() if run.created_at else None,
            "started_at": run.started_at.isoformat() if run.started_at else None,
            "finished_at": run.finished_at.isoformat() if run.finished_at else None,
            "total_jobs": run.total_jobs, "passed_filter": run.passed_filter,
            "ranked": run.ranked, "cvs_generated": run.cvs_generated,
            "error_message": run.error_message}
```

- [ ] **Step 5.4: Create Jinja2 templates**

`src/fitcv_cp/templates/base.html` — base layout with simple table styles and status color classes.

`src/fitcv_cp/templates/runs_list.html` — trigger button + table of recent runs linking to detail pages.

`src/fitcv_cp/templates/run_detail.html` — run metadata table + event timeline table.

*(Full HTML is in the spec; keep it minimal — no JS frameworks, just HTML + inline CSS.)*

- [ ] **Step 5.5: Run tests**

```bash
pytest tests/fitcv_cp/test_app.py -v
# Expected: 4 passed
```

- [ ] **Step 5.6: Commit**

```bash
git add src/fitcv_cp/app.py src/fitcv_cp/templates/ tests/fitcv_cp/test_app.py
git commit -m "feat(cp): add FastAPI admin app with HTML templates and REST API"
```

---

## Task 6 — Packaging, Dependencies, and Docker

**Files:**
- Modify: `requirements.txt`
- Create: `Dockerfile`
- Create: `docker-compose.yml`
- Create: `src/fitcv_cp/main.py`

- [ ] **Step 6.1: Update `requirements.txt`**

```
fastapi>=0.110.0
uvicorn[standard]>=0.29.0
jinja2>=3.1.0
rq>=1.16.0
redis>=5.0.0
httpx>=0.27.0
pytest-mock>=3.12.0
```

Install:
```bash
pip install -r requirements.txt
```

- [ ] **Step 6.2: Create `src/fitcv_cp/main.py`**

```python
# src/fitcv_cp/main.py
"""Uvicorn entrypoint for the FitCV admin web service."""
import os
from google.cloud import bigquery
from fitcv_cp.app import create_app

bq = bigquery.Client()
app = create_app(
    bq=bq,
    project=os.environ["GCP_PROJECT"],
    dataset=os.environ.get("BIGQUERY_DATASET", "fitcv"),
    redis_url=os.environ.get("REDIS_URL", "redis://redis:6379/0"),
)
```

- [ ] **Step 6.3: Write Dockerfile**

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY src/ ./src/
COPY config/ ./config/
COPY data/ ./data/
COPY templates/ ./templates/
COPY assets/ ./assets/
COPY pyproject.toml .
RUN pip install -e . --no-deps
ENV PYTHONUNBUFFERED=1
```

- [ ] **Step 6.4: Write `docker-compose.yml`**

```yaml
version: "3.9"
services:
  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]

  web:
    build: .
    command: uvicorn fitcv_cp.main:app --host 0.0.0.0 --port 8000 --reload
    ports: ["8000:8000"]
    environment:
      - GCP_PROJECT=${GCP_PROJECT}
      - BIGQUERY_DATASET=${BIGQUERY_DATASET:-fitcv}
      - REDIS_URL=redis://redis:6379/0
      - GOOGLE_APPLICATION_CREDENTIALS=/app/sa_key.json
    volumes:
      - .:/app
      - ./fitcv-491123-51c030d71e07.json:/app/sa_key.json:ro
    depends_on: [redis]

  worker:
    build: .
    command: rq worker fitcv --url redis://redis:6379/0
    environment:
      - GCP_PROJECT=${GCP_PROJECT}
      - BIGQUERY_DATASET=${BIGQUERY_DATASET:-fitcv}
      - REDIS_URL=redis://redis:6379/0
      - GOOGLE_APPLICATION_CREDENTIALS=/app/sa_key.json
    volumes:
      - .:/app
      - ./fitcv-491123-51c030d71e07.json:/app/sa_key.json:ro
    depends_on: [redis]
```

- [ ] **Step 6.5: Run full test suite**

```bash
pytest tests/ -v
# Expected: all existing + new tests pass
```

- [ ] **Step 6.6: Commit**

```bash
git add Dockerfile docker-compose.yml src/fitcv_cp/main.py requirements.txt
git commit -m "feat(cp): add Dockerfile, docker-compose, and uvicorn entrypoint"
```

---

## Task 7 — Bootstrap New BQ Tables + Smoke Test

**Files:**
- Modify: `scripts/bootstrap_bigquery.py`

- [ ] **Step 7.1: Register new DDL files in bootstrap script**

Add `pipeline_runs.sql` and `pipeline_run_events.sql` to the list of DDL files in `scripts/bootstrap_bigquery.py`, then run:

```bash
python scripts/bootstrap_bigquery.py
# Expected: pipeline_runs and pipeline_run_events created (or already exist message)
```

- [ ] **Step 7.2: Local docker-compose smoke test**

```bash
docker compose up --build -d
sleep 15  # wait for services

# Check web is up:
curl http://localhost:8000/runs
# Expected: []

# Trigger a run:
curl -X POST http://localhost:8000/runs \
  -H "Content-Type: application/json" \
  -d '{"jobs_path": "data/sample_jobs.json"}'
# Expected: {"run_id": "<uuid>"}

# Poll status (repeat until succeeded/failed):
curl http://localhost:8000/runs/<run_id>

# Check events:
curl http://localhost:8000/runs/<run_id>/events

# Open admin UI in browser:
# http://localhost:8000/admin/runs

docker compose down
```

- [ ] **Step 7.3: Commit**

```bash
git add scripts/bootstrap_bigquery.py
git commit -m "feat(cp): register control-plane BQ tables in bootstrap script"
```

---

## Verification Plan

### Automated Tests

```bash
# Existing pipeline suite — must remain green:
pytest tests/ --ignore=tests/fitcv_cp -v
# Expected: 274 passed, 7 skipped (same baseline)

# New control-plane suite:
pytest tests/fitcv_cp/ -v
# Expected: ~16 tests, all passed
```

### Manual Smoke Test (Docker)

```bash
docker compose up --build -d
sleep 15

# 1. Admin page loads:
open http://localhost:8000/admin/runs  # or: curl -s http://localhost:8000/admin/runs | head -20

# 2. Trigger a run via API:
RUN_ID=$(curl -s -X POST http://localhost:8000/runs \
  -H "Content-Type: application/json" \
  -d '{"jobs_path": "data/sample_jobs.json"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['run_id'])")

# 3. Poll until status is succeeded or failed:
curl http://localhost:8000/runs/$RUN_ID

# 4. Inspect event timeline:
curl http://localhost:8000/runs/$RUN_ID/events

# 5. Verify BigQuery rows via GCP Console:
#    BigQuery → fitcv dataset → pipeline_runs → Preview (should show 1 row)
#    BigQuery → fitcv dataset → pipeline_run_events → Preview (should show stage events)

docker compose down
```
