"""FastAPI admin control plane app."""
import datetime
import uuid
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, field_validator

from fitcv_cp.bq_store import get_events, get_run, insert_run, list_runs
from fitcv_cp.models import PipelineRun, RunStatus
from fitcv_cp.queue import enqueue_run

TEMPLATES_DIR = Path(__file__).parent / "templates"


class TriggerRequest(BaseModel):
    jobs_path: str = "data/sample_jobs.json"
    config_path: str = ".env.yaml"
    triggered_by: str = "admin"

    @field_validator("jobs_path")
    @classmethod
    def jobs_path_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("jobs_path must not be empty")
        return v


def create_app(bq: Any, project: str, dataset: str, redis_url: str) -> FastAPI:
    app = FastAPI(title="FitCV Admin Control Plane")
    templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

    @app.get("/healthz")
    def healthz() -> dict:
        return {"status": "ok"}

    @app.post("/runs", status_code=201)
    def trigger_run(req: TriggerRequest) -> dict:
        run_id = str(uuid.uuid4())
        # Insert FIRST — then enqueue. DB is the source of truth.
        run = PipelineRun(
            run_id=run_id,
            status=RunStatus.QUEUED,
            triggered_by=req.triggered_by,
            trigger_source="ui",
            jobs_path=req.jobs_path,
            config_path=req.config_path,
            created_at=datetime.datetime.now(datetime.timezone.utc),
        )
        insert_run(run, bq, project=project, dataset=dataset)
        enqueue_run(
            jobs_path=req.jobs_path,
            config_path=req.config_path,
            triggered_by=req.triggered_by,
            redis_url=redis_url,
            run_id=run_id,  # pass the pre-created run_id
        )
        return {"run_id": run_id}

    @app.get("/runs")
    def get_runs_list() -> list:
        return [_run_to_dict(r) for r in list_runs(bq, project=project, dataset=dataset)]

    @app.get("/runs/{run_id}")
    def get_run_detail(run_id: str) -> dict:
        run = get_run(run_id, bq, project=project, dataset=dataset)
        if run is None:
            raise HTTPException(status_code=404, detail="Run not found")
        return _run_to_dict(run)

    @app.get("/runs/{run_id}/events")
    def get_run_events_list(run_id: str) -> list:
        run = get_run(run_id, bq, project=project, dataset=dataset)
        if run is None:
            raise HTTPException(status_code=404, detail="Run not found")
        events = get_events(run_id, bq, project=project, dataset=dataset)
        return [
            {
                "event_id": e.event_id,
                "stage": e.stage,
                "level": e.level,
                "message": e.message,
                "created_at": e.created_at.isoformat() if hasattr(e.created_at, "isoformat") else str(e.created_at),
            }
            for e in events
        ]

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
        return templates.TemplateResponse(
            "run_detail.html", {"request": request, "run": run, "events": events}
        )

    return app


def _run_to_dict(run: PipelineRun) -> dict:
    return {
        "run_id": run.run_id,
        "status": run.status.value,
        "triggered_by": run.triggered_by,
        "jobs_path": run.jobs_path,
        "created_at": run.created_at.isoformat() if run.created_at else None,
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "finished_at": run.finished_at.isoformat() if run.finished_at else None,
        "total_jobs": run.total_jobs,
        "passed_filter": run.passed_filter,
        "ranked": run.ranked,
        "cvs_generated": run.cvs_generated,
        "error_message": run.error_message,
        "error_stage": run.error_stage,
    }
