"""FastAPI admin control plane app."""
import datetime
import json as _json
import uuid
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request, UploadFile, File, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, field_validator

from fitcv.config import load_config
from fitcv_cp.bq_store import (
    append_event,
    archive_run,
    get_events, get_run, insert_run, list_filter_results_for_run,
    list_runs, list_cvs_for_run, get_cv_markdown, list_run_structured_jobs,
    request_run_cancel, unarchive_run, update_run_queue_job_id,
)
from fitcv_cp.models import PipelineRun, RunEvent, RunStatus
from fitcv_cp.queue import cancel_queued_run, enqueue_run, enqueue_run_with_job_id
from fitcv_cp.settings_schema import (
    RANKING_GROUPS,
    SETTINGS_SCHEMA,
    SETTINGS_SECTIONS,
    ValidationError,
    apply_settings_to_config,
    coerce_value,
    validate_settings,
)
from fitcv_cp.settings_store import load_active_settings, save_setting, save_settings_group

TEMPLATES_DIR = Path(__file__).parent / "templates"


class TriggerRequest(BaseModel):
    jobs_path: str = "data/sample_jobs.json"
    config_path: str = ".env.yaml"
    triggered_by: str = "admin"
    config_overrides: dict[str, Any] = {}

    @field_validator("jobs_path")
    @classmethod
    def jobs_path_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("jobs_path must not be empty")
        return v


class SettingUpdate(BaseModel):
    value: Any
    updated_by: str = "admin"


def create_app(bq: Any, project: str, dataset: str, redis_url: str) -> FastAPI:
    app = FastAPI(title="FitCV Admin Control Plane")
    templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

    @app.get("/healthz")
    def healthz() -> dict:
        return {"status": "ok"}

    def _execute_trigger(jobs_path: str, config_path: str, triggered_by: str, config_overrides: dict[str, Any]) -> dict:
        # Build effective config: YAML → BQ settings → per-run overrides
        base_config = load_config(config_path)
        active_settings = load_active_settings(bq=bq, project=project, dataset=dataset)

        # Coerce and validate per-run overrides using the same schema
        coerced_overrides: dict[str, Any] = {}
        for k, v in config_overrides.items():
            try:
                coerced_overrides[k] = coerce_value(k, v)
            except KeyError:
                raise HTTPException(status_code=422, detail=f"Unknown setting key: {k!r}")
            except (ValueError, TypeError) as exc:
                raise HTTPException(status_code=422, detail=str(exc))
        try:
            validate_settings(coerced_overrides)
        except ValidationError as exc:
            raise HTTPException(status_code=422, detail=str(exc))

        # Merge: YAML < BQ settings < per-run overrides
        effective_config = dict(base_config)
        apply_settings_to_config(effective_config, active_settings)
        apply_settings_to_config(effective_config, coerced_overrides)

        run_id = str(uuid.uuid4())
        # Insert FIRST — then enqueue. DB is the source of truth.
        run = PipelineRun(
            run_id=run_id,
            status=RunStatus.QUEUED,
            triggered_by=triggered_by,
            trigger_source="ui",
            jobs_path=jobs_path,
            config_path=config_path,
            created_at=datetime.datetime.now(datetime.timezone.utc),
            effective_settings_json=_json.dumps(effective_config),
        )
        insert_run(run, bq, project=project, dataset=dataset)
        _, queue_job_id = enqueue_run_with_job_id(
            jobs_path=jobs_path,
            config_path=config_path,
            triggered_by=triggered_by,
            redis_url=redis_url,
            run_id=run_id,
        )
        update_run_queue_job_id(run_id, queue_job_id, bq, project=project, dataset=dataset)
        return {"run_id": run_id}

    def _execute_trigger_with_inputs(
        jobs_path: str,
        config_path: str,
        triggered_by: str,
        config_overrides: dict[str, Any],
        *,
        jobs_input_source: str | None = None,
        jobs_input_json: str | None = None,
        candidate_profile_source: str | None = None,
        candidate_profile_json: str | None = None,
    ) -> dict:
        """Like _execute_trigger but records run-scoped input metadata."""
        # Build effective config: YAML → BQ settings → per-run overrides
        base_config = load_config(config_path)
        active_settings = load_active_settings(bq=bq, project=project, dataset=dataset)
        coerced_overrides: dict[str, Any] = {}
        for k, v in config_overrides.items():
            try:
                coerced_overrides[k] = coerce_value(k, v)
            except KeyError:
                raise HTTPException(status_code=422, detail=f"Unknown setting key: {k!r}")
            except (ValueError, TypeError) as exc:
                raise HTTPException(status_code=422, detail=str(exc))
        try:
            validate_settings(coerced_overrides)
        except ValidationError as exc:
            raise HTTPException(status_code=422, detail=str(exc))
        effective_config = dict(base_config)
        apply_settings_to_config(effective_config, active_settings)
        apply_settings_to_config(effective_config, coerced_overrides)

        # Inject runtime candidate profile override
        if candidate_profile_json:
            effective_config.setdefault("runtime_inputs", {})["candidate_profile_json"] = candidate_profile_json

        run_id = str(uuid.uuid4())
        run = PipelineRun(
            run_id=run_id,
            status=RunStatus.QUEUED,
            triggered_by=triggered_by,
            trigger_source="ui",
            jobs_path=jobs_path,
            config_path=config_path,
            created_at=datetime.datetime.now(datetime.timezone.utc),
            effective_settings_json=_json.dumps(effective_config),
            jobs_input_source=jobs_input_source,
            jobs_input_json=jobs_input_json,
            candidate_profile_source=candidate_profile_source,
            candidate_profile_json=candidate_profile_json,
        )
        insert_run(run, bq, project=project, dataset=dataset)
        _, queue_job_id = enqueue_run_with_job_id(
            jobs_path=jobs_path,
            config_path=config_path,
            triggered_by=triggered_by,
            redis_url=redis_url,
            run_id=run_id,
        )
        update_run_queue_job_id(run_id, queue_job_id, bq, project=project, dataset=dataset)
        return {"run_id": run_id}

    @app.post("/runs", status_code=201)
    def trigger_run(req: TriggerRequest) -> dict:
        return _execute_trigger(
            jobs_path=req.jobs_path,
            config_path=req.config_path,
            triggered_by=req.triggered_by,
            config_overrides=req.config_overrides,
        )

    @app.post("/admin/upload-trigger", status_code=201)
    async def upload_trigger(
        jobs_file: UploadFile = File(None),
        jobs_path: str = Form("data/sample_jobs.json"),
        jobs_input_mode: str = Form("path"),      # "path" | "upload" | "paste"
        jobs_text: str = Form(""),
        config_path: str = Form(".env.yaml"),
        candidate_profile_mode: str = Form("default_config"),  # "default_config" | "upload" | "paste"
        candidate_profile_file: UploadFile = File(None),
        candidate_profile_text: str = Form(""),
    ) -> dict:
        from fitcv.candidate import load_profile_json_text as _load_json_profile
        from fastapi import HTTPException as _HTTPEx

        upload_dir = Path("data/uploads")
        upload_dir.mkdir(parents=True, exist_ok=True)

        # ── Jobs input resolution ──────────────────────────────────────
        jobs_input_json_snapshot: str | None = None
        if jobs_input_mode == "path":
            if not jobs_path or not jobs_path.strip():
                raise HTTPException(status_code=422, detail="jobs_path required for path mode")
            actual_jobs_path = jobs_path
            jobs_input_source = "path"
        elif jobs_input_mode == "upload":
            if not jobs_file or not jobs_file.filename:
                raise HTTPException(status_code=422, detail="jobs_file required for upload mode")
            raw_bytes = await jobs_file.read()
            save_path = upload_dir / f"{uuid.uuid4().hex}_{jobs_file.filename}"
            with open(save_path, "wb") as f:
                f.write(raw_bytes)
            actual_jobs_path = str(save_path)
            jobs_input_source = "upload"
            # Capture immutable snapshot (same audit behaviour as paste mode)
            try:
                _parsed = _json.loads(raw_bytes.decode("utf-8"))
                jobs_input_json_snapshot = _json.dumps(_parsed, ensure_ascii=False, indent=2)
            except (_json.JSONDecodeError, UnicodeDecodeError):
                jobs_input_json_snapshot = None  # invalid JSON upload; pipeline will surface the error
        elif jobs_input_mode == "paste":
            if not jobs_text or not jobs_text.strip():
                raise HTTPException(status_code=422, detail="jobs_text required for paste mode")
            try:
                parsed_jobs = _json.loads(jobs_text)
            except _json.JSONDecodeError as exc:
                raise HTTPException(status_code=422, detail=f"Invalid JSON in jobs_text: {exc}")
            if not isinstance(parsed_jobs, list):
                raise HTTPException(status_code=422, detail="jobs_text must be a JSON array of objects")
            canonical = _json.dumps(parsed_jobs, ensure_ascii=False, indent=2)
            paste_file = upload_dir / f"{uuid.uuid4().hex}_pasted_jobs.json"
            paste_file.write_text(canonical, encoding="utf-8")
            actual_jobs_path = str(paste_file)
            jobs_input_source = "paste"
            jobs_input_json_snapshot = canonical
        else:
            raise HTTPException(status_code=422, detail=f"Unknown jobs_input_mode: {jobs_input_mode!r}")

        # ── Candidate profile resolution ─────────────────────────────────
        candidate_json_snapshot: str | None = None
        if candidate_profile_mode == "default_config":
            candidate_profile_source = "default_config"
        elif candidate_profile_mode == "upload":
            if not candidate_profile_file or not candidate_profile_file.filename:
                raise HTTPException(status_code=422, detail="candidate_profile_file required for upload mode")
            raw_bytes = await candidate_profile_file.read()
            raw_text = raw_bytes.decode("utf-8")
            try:
                _load_json_profile(raw_text)  # validate
            except ValueError as exc:
                raise HTTPException(status_code=422, detail=str(exc))
            candidate_json_snapshot = _json.dumps(_json.loads(raw_text), ensure_ascii=False, indent=2)
            candidate_profile_source = "upload"
        elif candidate_profile_mode == "paste":
            if not candidate_profile_text or not candidate_profile_text.strip():
                raise HTTPException(status_code=422, detail="candidate_profile_text required for paste mode")
            try:
                _load_json_profile(candidate_profile_text)  # validate
            except ValueError as exc:
                raise HTTPException(status_code=422, detail=str(exc))
            candidate_json_snapshot = _json.dumps(
                _json.loads(candidate_profile_text), ensure_ascii=False, indent=2
            )
            candidate_profile_source = "paste"
        else:
            raise HTTPException(status_code=422, detail=f"Unknown candidate_profile_mode: {candidate_profile_mode!r}")

        return _execute_trigger_with_inputs(
            jobs_path=actual_jobs_path,
            config_path=config_path,
            triggered_by="admin",
            config_overrides={},
            jobs_input_source=jobs_input_source,
            jobs_input_json=jobs_input_json_snapshot,
            candidate_profile_source=candidate_profile_source,
            candidate_profile_json=candidate_json_snapshot,
        )

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

    @app.get("/settings")
    def get_settings_view() -> dict:
        return load_active_settings(bq=bq, project=project, dataset=dataset)

    @app.post("/settings/{key}", status_code=200)
    def update_setting(key: str, body: SettingUpdate) -> dict:
        try:
            coerced = coerce_value(key, body.value)
        except KeyError:
            raise HTTPException(status_code=422, detail=f"Unknown setting key: {key!r}")
        except (ValueError, TypeError) as exc:
            raise HTTPException(status_code=422, detail=str(exc))
        try:
            validate_settings({key: coerced})
        except ValidationError as exc:
            raise HTTPException(status_code=422, detail=str(exc))
        save_setting(key, coerced, updated_by=body.updated_by, bq=bq, project=project, dataset=dataset)
        return {"key": key, "value": coerced}

    @app.get("/admin/settings", response_class=HTMLResponse)
    def admin_settings_view(request: Request) -> HTMLResponse:
        active = load_active_settings(bq=bq, project=project, dataset=dataset)
        return templates.TemplateResponse(
            request=request,
            name="settings.html",
            context={
                "schema": SETTINGS_SCHEMA,
                "active": active,
                "ranking_weight_keys": RANKING_GROUPS["ranking-weights"],
                "ranking_groups": RANKING_GROUPS,
            }
        )

    @app.post("/admin/settings/{key}", response_class=HTMLResponse)
    async def admin_settings_update_key(request: Request, key: str) -> HTMLResponse:
        from fastapi import Form
        from fastapi.responses import RedirectResponse
        form = await request.form()
        value = form.get("value", "")
        try:
            coerced = coerce_value(key, value)
            validate_settings({key: coerced})
        except (KeyError, ValidationError, ValueError) as exc:
            active = load_active_settings(bq=bq, project=project, dataset=dataset)
            return templates.TemplateResponse(
                request=request,
                name="settings.html",
                context={"schema": SETTINGS_SCHEMA, "active": active, "error": str(exc)},
                status_code=422,
            )
        save_setting(key, coerced, updated_by="admin", bq=bq, project=project, dataset=dataset)
        return RedirectResponse("/admin/settings", status_code=303)

    @app.post("/admin/settings/group/{group_name}", response_class=HTMLResponse)
    async def admin_settings_update_group(
        request: Request, group_name: str
    ) -> HTMLResponse:
        from uuid import uuid4
        from fastapi.responses import RedirectResponse

        if group_name not in RANKING_GROUPS:
            raise HTTPException(status_code=404, detail=f"Unknown group: {group_name!r}")

        keys = RANKING_GROUPS[group_name]
        form = await request.form()

        # Coerce all keys in the group
        coerced: dict = {}
        coerce_errors: list[str] = []
        for key in keys:
            raw = form.get(key, "")
            try:
                coerced[key] = coerce_value(key, raw)
            except (KeyError, ValueError) as exc:
                coerce_errors.append(str(exc))

        def _get_active() -> dict:
            return load_active_settings(bq=bq, project=project, dataset=dataset)

        def _error_response(msg: str) -> HTMLResponse:
            active = _get_active()
            return templates.TemplateResponse(
                request=request,
                name="settings.html",
                context={
                    "schema": SETTINGS_SCHEMA,
                    "active": active,
                    "ranking_weight_keys": RANKING_GROUPS["ranking-weights"],
                    "ranking_groups": RANKING_GROUPS,
                    "group_error": {group_name: msg},
                    "group_draft": {group_name: dict(form)},
                },
                status_code=422,
            )

        if coerce_errors:
            return _error_response("; ".join(coerce_errors))

        # Validate full group as one coherent payload — no write occurs on failure
        try:
            validate_settings(coerced)
        except ValidationError as exc:
            return _error_response(str(exc))

        # Generate shared audit identity for this grouped save
        update_id = str(uuid4())
        updated_by = f"admin:grp:{update_id}"

        # Write — surface BQ failures to the user
        try:
            save_settings_group(
                coerced, updated_by=updated_by, bq=bq, project=project, dataset=dataset
            )
        except RuntimeError as exc:
            return _error_response(f"Save failed: {exc}")

        return RedirectResponse("/admin/settings", status_code=303)

    @app.post("/admin/settings/section/{section_name}", response_class=HTMLResponse)
    async def admin_settings_section_save(
        request: Request, section_name: str
    ) -> HTMLResponse:
        """Section-level save for retrieval, timing, and global-job-filters.

        Each key is validated independently (no cross-key constraints within a section).
        A 422 is returned if any value fails validation, with section_errors populated
        so the template can highlight offending fields.
        """
        from uuid import uuid4
        from fastapi.responses import RedirectResponse as _Redirect

        if section_name not in SETTINGS_SECTIONS:
            raise HTTPException(status_code=404, detail=f"Unknown section: {section_name!r}")

        keys = SETTINGS_SECTIONS[section_name]
        form = await request.form()

        coerced: dict = {}
        section_errors: dict[str, str] = {}

        for key in keys:
            raw = form.get(key, "")
            try:
                coerced[key] = coerce_value(key, raw)
            except (KeyError, ValueError) as exc:
                section_errors[key] = str(exc)

        # Run cross-key validation across all coerced values in this section
        if not section_errors:
            try:
                validate_settings(coerced)
            except ValidationError as exc:
                section_errors[keys[0]] = str(exc)

        def _section_error_response(errors: dict[str, str]) -> HTMLResponse:
            active = load_active_settings(bq=bq, project=project, dataset=dataset)
            return templates.TemplateResponse(
                request=request,
                name="settings.html",
                context={
                    "schema": SETTINGS_SCHEMA,
                    "active": active,
                    "ranking_weight_keys": RANKING_GROUPS["ranking-weights"],
                    "ranking_groups": RANKING_GROUPS,
                    "section_errors": errors,
                    "section_draft": {key: form.get(key, "") for key in keys},
                },
                status_code=422,
            )

        if section_errors:
            return _section_error_response(section_errors)

        update_id = str(uuid4())
        updated_by = f"admin:section:{update_id}"
        try:
            save_settings_group(
                coerced, updated_by=updated_by, bq=bq, project=project, dataset=dataset
            )
        except RuntimeError as exc:
            return _section_error_response({keys[0]: f"Save failed: {exc}"})

        return _Redirect("/admin/settings", status_code=303)

    @app.get("/admin/runs", response_class=HTMLResponse)
    def admin_runs(request: Request) -> HTMLResponse:
        view = request.query_params.get("view", "active")
        if view == "archived":
            runs = list_runs(bq, project=project, dataset=dataset, archived_only=True)
        elif view == "all":
            runs = list_runs(bq, project=project, dataset=dataset, include_archived=True)
        else:  # default: active
            runs = list_runs(bq, project=project, dataset=dataset, include_archived=False)
        return templates.TemplateResponse(
            request=request, name="runs_list.html",
            context={"runs": runs, "view": view}
        )

    @app.post("/admin/runs/{run_id}/stop")
    def admin_stop_run(run_id: str) -> dict:
        """Stop a queued or running run. Returns JSON for fetch() callers."""
        run = get_run(run_id, bq, project=project, dataset=dataset)
        if run is None:
            raise HTTPException(status_code=404, detail="Run not found")
        eligible = {RunStatus.QUEUED, RunStatus.RUNNING}
        if run.status not in eligible:
            raise HTTPException(
                status_code=409,
                detail=f"Cannot stop run with status '{run.status.value}'",
            )
        now = datetime.datetime.now(datetime.timezone.utc)
        event_id = str(uuid.uuid4())
        if run.status == RunStatus.QUEUED and run.queue_job_id:
            cancelled_in_queue = cancel_queued_run(run.queue_job_id, redis_url=redis_url)
            if cancelled_in_queue:
                # Job still in queue — mark directly cancelled
                request_run_cancel(run_id, "admin", RunStatus.CANCELLED.value, bq, project=project, dataset=dataset)
                append_event(
                    RunEvent(
                        run_id=run_id, event_id=event_id, stage="cancel_requested",
                        level="warning", message="Stop requested — cancelled from queue",
                        created_at=now,
                    ),
                    bq, project=project, dataset=dataset,
                )
                append_event(
                    RunEvent(
                        run_id=run_id, event_id=str(uuid.uuid4()), stage="run_cancelled",
                        level="warning", message="Run cancelled before pipeline execution",
                        created_at=now,
                    ),
                    bq, project=project, dataset=dataset,
                )
                return {"status": "cancelled", "run_id": run_id}
        # Running (or queued but already claimed) — set cancelling
        request_run_cancel(run_id, "admin", RunStatus.CANCELLING.value, bq, project=project, dataset=dataset)
        append_event(
            RunEvent(
                run_id=run_id, event_id=event_id, stage="cancel_requested",
                level="warning", message="Stop requested — run will be cancelled at next checkpoint",
                created_at=now,
            ),
            bq, project=project, dataset=dataset,
        )
        return {"status": "cancelling", "run_id": run_id}

    @app.post("/admin/runs/{run_id}/archive")
    def admin_archive_run(run_id: str) -> dict:
        """Archive a terminal run. Returns JSON for fetch() callers."""
        run = get_run(run_id, bq, project=project, dataset=dataset)
        if run is None:
            raise HTTPException(status_code=404, detail="Run not found")
        eligible = {RunStatus.SUCCEEDED, RunStatus.FAILED, RunStatus.CANCELLED}
        if run.status not in eligible:
            raise HTTPException(
                status_code=409,
                detail=f"Cannot archive run with status '{run.status.value}'",
            )
        if run.archived_at is not None:
            raise HTTPException(status_code=409, detail="Run is already archived")
        archive_run(run_id, "admin", bq, project=project, dataset=dataset)
        append_event(
            RunEvent(
                run_id=run_id, event_id=str(uuid.uuid4()), stage="run_archived",
                level="info", message="Run archived by admin",
                created_at=datetime.datetime.now(datetime.timezone.utc),
            ),
            bq, project=project, dataset=dataset,
        )
        return {"status": "archived", "run_id": run_id}

    @app.post("/admin/runs/{run_id}/unarchive")
    def admin_unarchive_run(run_id: str) -> dict:
        """Unarchive a run, returning it to the active list. Returns JSON for fetch() callers."""
        run = get_run(run_id, bq, project=project, dataset=dataset)
        if run is None:
            raise HTTPException(status_code=404, detail="Run not found")
        if run.archived_at is None:
            raise HTTPException(status_code=409, detail="Run is not archived")
        unarchive_run(run_id, bq, project=project, dataset=dataset)
        append_event(
            RunEvent(
                run_id=run_id, event_id=str(uuid.uuid4()), stage="run_unarchived",
                level="info", message="Run unarchived by admin",
                created_at=datetime.datetime.now(datetime.timezone.utc),
            ),
            bq, project=project, dataset=dataset,
        )
        return {"status": "unarchived", "run_id": run_id}

    @app.get("/admin/runs/{run_id}", response_class=HTMLResponse)
    def admin_run_detail(request: Request, run_id: str) -> HTMLResponse:
        run = get_run(run_id, bq, project=project, dataset=dataset)
        if run is None:
            raise HTTPException(status_code=404)
        events = get_events(run_id, bq, project=project, dataset=dataset)
        cv_versions = list_cvs_for_run(run_id, bq, project=project, dataset=dataset)
        enriched_jobs = list_run_structured_jobs(run_id, bq, project=project, dataset=dataset)
        filter_results = list_filter_results_for_run(run_id, bq, project=project, dataset=dataset)

        # Build per-job filter outcome lookup: job_url → {passed, reasons}
        filter_results_by_job_url: dict[str, dict] = {
            row["job_url"]: row for row in filter_results
        }

        # Jobs rejected before enrichment have filter_results rows but no enriched row.
        enriched_job_urls = {j["job_url"] for j in enriched_jobs}
        pre_enrichment_rejects = [
            row for row in filter_results
            if row["job_url"] not in enriched_job_urls and row.get("reasons")
        ]

        # Candidate profile display
        candidate_profile_parsed: dict | None = None
        candidate_profile_pretty: str | None = None
        if run.candidate_profile_json:
            try:
                candidate_profile_parsed = _json.loads(run.candidate_profile_json)
                candidate_profile_pretty = _json.dumps(candidate_profile_parsed, indent=2, ensure_ascii=False)
            except (_json.JSONDecodeError, TypeError):
                candidate_profile_pretty = run.candidate_profile_json

        return templates.TemplateResponse(
            request=request, name="run_detail.html", context={
                "run": run,
                "events": events,
                "cv_versions": cv_versions,
                "enriched_jobs": enriched_jobs,
                "filter_results_by_job_url": filter_results_by_job_url,
                "pre_enrichment_rejects": pre_enrichment_rejects,
                "candidate_profile_parsed": candidate_profile_parsed,
                "candidate_profile_pretty": candidate_profile_pretty,
            }
        )

    @app.get("/admin/cvs/{version_id}/download")
    def download_cv(version_id: str):
        from fastapi import Response
        content = get_cv_markdown(version_id, bq, project=project, dataset=dataset)
        if content is None:
            raise HTTPException(status_code=404, detail="CV not found")
        return Response(
            content=content,
            media_type="text/markdown",
            headers={"Content-Disposition": f'attachment; filename="cv_{version_id}.md"'}
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
