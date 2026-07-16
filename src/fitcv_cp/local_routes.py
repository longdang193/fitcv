"""@meta
name: local_routes
type: utility
domain: fitcv_local
ownership: feature
responsibility:
  - Serve packaged onboarding and readiness routes.
  - Persist non-secret onboarding progress under user data root.
inputs:
  - Browser form data and local setup services
outputs:
  - Resumable onboarding state and user configuration
capabilities:
  - admin_control_plane_core.jinja2-admin-pages
  - settings_system.settings-schema-registry
  - trigger_run_management.run-health-surface
  - run_lifecycle_controls.state-aware-max-runtime-timeout-handling-for-queued-running-cancelling-and-paused-manual-runs
lifecycle:
  - status: active
"""

from __future__ import annotations

import json
import io
import os
import platform
import re
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import yaml
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates

from fitcv.candidate import load_profile_text
from fitcv_cp.local_credentials import credential_is_configured, get_credential, set_credential
from fitcv_cp.local_setup import (
    ProviderSetup,
    build_routing_overlay,
    discover_models,
    readiness,
    test_provider,
    write_routing_overlay,
)
from fitcv_cp.local_storage import (
    MAX_BACKUP_ARCHIVE_BYTES,
    LocalStoragePaths,
    create_backup_archive,
    default_pending_operation_path,
    inspect_local_storage,
    restore_backup_archive,
    sqlite_schema_version,
    validate_data_root_destination,
    write_pending_operation,
)


ONBOARDING_STEPS = ("welcome", "data", "profile", "provider", "models", "review", "complete")
PROVIDER_DRAFT_FIELDS = (
    "provider_id",
    "provider_type",
    "display_name",
    "base_url",
    "auth_mode",
    "wire_api",
    "timeout_seconds",
    "default_model",
    "enrich_extraction",
    "ranking_ai_score",
    "cv_generation_structured_write",
    "synonym_triage_recommendation",
)
ACTIVE_RUN_STATUSES = {"queued", "running", "awaiting_continue", "cancelling"}
SENSITIVE_LOG_PATTERN = re.compile(
    r"authorization|bearer|api[_ -]?key|token|secret|password|prompt|candidate|profile|job description|cv text",
    re.IGNORECASE,
)
SAFE_LOG_PATTERN = re.compile(
    r"^(?:DEBUG|INFO|WARNING|ERROR) (?:startup|shutdown|health|backup|relocation|import|reconciliation)[A-Za-z0-9 .:_-]*$",
    re.IGNORECASE,
)


def _data_root() -> Path:
    value = str(os.environ.get("FITCV_LOCAL_DATA_ROOT") or "").strip()
    if not value:
        raise RuntimeError("FITCV_LOCAL_DATA_ROOT is not configured")
    return Path(value)


def _state_path() -> Path:
    return _data_root() / "onboarding.json"

def _local_paths() -> LocalStoragePaths:
    data_root = _data_root()
    return LocalStoragePaths(
        bootstrap_path=Path(os.environ["APPDATA"]) / "FitCV" / "bootstrap.json",
        data_root=data_root,
        sqlite_path=Path(os.environ["FITCV_CP_SQLITE_PATH"]),
        candidate_profile_path=Path(os.environ["FITCV_LOCAL_CANDIDATE_PROFILE_PATH"]),
        routing_overlay_path=Path(os.environ["FITCV_LOCAL_ROUTING_OVERLAY_PATH"]),
        artifacts_path=Path(os.environ["FITCV_LOCAL_ARTIFACTS_PATH"]),
        exports_path=Path(os.environ["FITCV_LOCAL_EXPORTS_PATH"]),
        logs_path=Path(os.environ["FITCV_LOCAL_LOGS_PATH"]),
        backups_path=Path(os.environ["FITCV_LOCAL_BACKUPS_PATH"]),
        uploads_path=Path(os.environ["FITCV_LOCAL_UPLOADS_PATH"]),
        temporary_path=Path(os.environ["FITCV_LOCAL_TEMP_PATH"]),
    )

def active_work_reasons(request: Request) -> list[str]:
    reasons: list[str] = []
    executor = getattr(request.app.state, "local_job_executor", None)
    if executor is not None and executor.is_busy():
        reasons.append("Local executor has active work")
    store = getattr(request.app.state, "run_store", None)
    if store is not None:
        try:
            active = [
                run.run_id
                for run in store.list_runs(limit=500, include_archived=True)
                if str(getattr(run, "status", "")).strip().lower().removeprefix("runstatus.")
                in ACTIVE_RUN_STATUSES
            ]
        except Exception:
            reasons.append("Run state could not be verified")
        else:
            if active:
                reasons.append(f"Active runs: {', '.join(active)}")
    return reasons

def _require_idle(request: Request) -> None:
    reasons = active_work_reasons(request)
    if reasons:
        raise HTTPException(status_code=409, detail=reasons)

def _signal_shutdown(request: Request) -> None:
    if bool(getattr(request.app.state, "local_draining", False)):
        return
    request.app.state.local_draining = True
    callback = getattr(request.app.state, "local_shutdown_callback", None)
    if callback is not None:
        callback()


def load_onboarding_state() -> dict[str, Any]:
    path = _state_path()
    if not path.exists():
        return {"version": 1, "current_step": "welcome", "complete": False, "provider_test_ok": False}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise RuntimeError("FitCV Local onboarding state is malformed") from exc
    if not isinstance(payload, dict) or payload.get("version") != 1:
        raise RuntimeError("FitCV Local onboarding state has unsupported schema")
    return payload


def save_onboarding_state(payload: dict[str, Any]) -> None:
    path = _state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
            json.dump(payload, handle, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
            temporary = Path(handle.name)
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()

def _save_feedback(section: str, *, draft: Any, error: str | None) -> None:
    state = load_onboarding_state()
    drafts = dict(state.get("drafts") or {})
    errors = dict(state.get("errors") or {})
    drafts[section] = draft
    if error:
        errors[section] = error
    else:
        errors.pop(section, None)
    state.update({"drafts": drafts, "errors": errors})
    save_onboarding_state(state)

def _write_profile(path: Path, profile: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
            yaml.safe_dump(profile, handle, sort_keys=False)
            handle.flush()
            os.fsync(handle.fileno())
            temporary = Path(handle.name)
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def onboarding_is_complete() -> bool:
    try:
        return bool(load_onboarding_state().get("complete"))
    except RuntimeError:
        return False


def _provider_setup(form: Any) -> ProviderSetup:
    provider_id = str(form.get("provider_id") or "openai_compatible").strip().lower()
    default_model = str(form.get("default_model") or "").strip()
    return ProviderSetup(
        provider_id=provider_id,
        provider_type=str(form.get("provider_type") or ("openai" if provider_id == "openai" else "openai_compatible")).strip().lower(),  # type: ignore[arg-type]
        display_name=str(form.get("display_name") or "OpenAI-compatible").strip(),
        base_url=str(form.get("base_url") or "").strip(),
        auth_mode=str(form.get("auth_mode") or "required").strip().lower(),  # type: ignore[arg-type]
        wire_api=str(form.get("wire_api") or "responses").strip().lower(),  # type: ignore[arg-type]
        timeout_seconds=float(str(form.get("timeout_seconds") or "120")),
        default_model=default_model,
        task_models={part: str(form.get(part) or default_model).strip() for part in (
            "enrich_extraction",
            "ranking_ai_score",
            "cv_generation_structured_write",
            "synonym_triage_recommendation",
        )},
    )

def _provider_draft(form: Any) -> dict[str, str]:
    return {field: str(form.get(field) or "").strip() for field in PROVIDER_DRAFT_FIELDS}

def _configured_provider_setup() -> ProviderSetup | None:
    state = load_onboarding_state()
    provider_id = str(state.get("provider_id") or "openai_compatible")
    overlay_path = Path(os.environ["FITCV_LOCAL_ROUTING_OVERLAY_PATH"])
    if not overlay_path.exists():
        return None
    overlay = yaml.safe_load(overlay_path.read_text(encoding="utf-8")) or {}
    provider = dict((overlay.get("providers") or {}).get(provider_id) or {})
    if not provider:
        return None
    parts = dict((overlay.get("model_routing") or {}).get("parts") or {})
    default_model = str((parts.get("cv_generation_structured_write") or {}).get("model") or "")
    return ProviderSetup(
        provider_id=provider_id,
        provider_type=str(provider.get("type") or "openai_compatible"),  # type: ignore[arg-type]
        display_name=str(provider.get("display_name") or provider_id),
        base_url=str(provider.get("base_url") or ""),
        auth_mode=str(provider.get("auth_mode") or "required"),  # type: ignore[arg-type]
        wire_api=str(provider.get("wire_api") or "responses"),  # type: ignore[arg-type]
        timeout_seconds=float(provider.get("timeout_seconds") or 120),
        default_model=default_model,
        task_models={part: str((parts.get(part) or {}).get("model") or "") for part in parts},
    )

def local_readiness_status() -> dict[str, object]:
    state = load_onboarding_state()
    reasons: list[str] = []
    if not state.get("profile_configured"):
        reasons.append("Candidate profile is not configured")
    setup = _configured_provider_setup()
    if setup is None:
        reasons.append("Provider routing is not configured")
        return {"ready": False, "reasons": reasons}
    provider_status = readiness(
        setup,
        credential_configured=credential_is_configured(setup.provider_id),
        provider_test_ok=bool(state.get("provider_test_ok")),
    )
    reasons.extend(str(reason) for reason in provider_status["reasons"])
    return {**provider_status, "ready": not reasons, "reasons": reasons}


def build_local_router(templates: Jinja2Templates) -> APIRouter:
    router = APIRouter(prefix="/local")

    @router.get("/onboarding")
    async def onboarding(request: Request):
        state = load_onboarding_state()
        profile_path = Path(os.environ["FITCV_LOCAL_CANDIDATE_PROFILE_PATH"])
        profile_draft = str((state.get("drafts") or {}).get("profile") or "")
        if not profile_draft and profile_path.exists():
            profile_draft = profile_path.read_text(encoding="utf-8")
        return templates.TemplateResponse(
            request=request,
            name="local_onboarding.html",
            context={"state": state, "data_root": str(_data_root()), "profile_draft": profile_draft},
        )

    @router.post("/onboarding/profile")
    async def save_profile(request: Request):
        form = await request.form()
        raw_profile = str(form.get("profile") or "")
        try:
            profile = load_profile_text(raw_profile)
        except ValueError as exc:
            _save_feedback("profile", draft=raw_profile, error=str(exc))
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        profile_path = Path(os.environ["FITCV_LOCAL_CANDIDATE_PROFILE_PATH"])
        _write_profile(profile_path, profile)
        _save_feedback("profile", draft=raw_profile, error=None)
        state = load_onboarding_state()
        state.update({"current_step": "provider", "profile_configured": True})
        save_onboarding_state(state)
        return RedirectResponse("/local/onboarding", status_code=303)

    @router.post("/onboarding/provider")
    async def save_provider(request: Request):
        form = await request.form()
        draft = _provider_draft(form)
        try:
            setup = _provider_setup(form)
            overlay = build_routing_overlay(setup)
        except (TypeError, ValueError) as exc:
            _save_feedback("provider", draft=draft, error=str(exc))
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        api_key = str(form.get("api_key") or "").strip()
        if api_key:
            set_credential(setup.provider_id, api_key)
        write_routing_overlay(Path(os.environ["FITCV_LOCAL_ROUTING_OVERLAY_PATH"]), overlay)
        _save_feedback("provider", draft=draft, error=None)
        state = load_onboarding_state()
        state.update(
            {
                "current_step": "models",
                "provider_id": setup.provider_id,
                "provider_test_ok": False,
            }
        )
        save_onboarding_state(state)
        return RedirectResponse("/local/onboarding", status_code=303)

    @router.post("/onboarding/models/discover")
    async def discover_provider_models(request: Request) -> JSONResponse:
        form = await request.form()
        try:
            setup = _provider_setup(form)
            build_routing_overlay(setup)
        except (TypeError, ValueError) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        api_key = str(form.get("api_key") or "").strip() or get_credential(setup.provider_id) or ""
        try:
            models = discover_models(setup, api_key=api_key)
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Model discovery failed: {exc}") from exc
        state = load_onboarding_state()
        state["discovered_models"] = models
        save_onboarding_state(state)
        return JSONResponse({"models": models})

    @router.post("/onboarding/provider/test")
    async def run_provider_test(request: Request) -> JSONResponse:
        form = await request.form()
        try:
            setup = _provider_setup(form)
            build_routing_overlay(setup)
        except (TypeError, ValueError) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        api_key = str(form.get("api_key") or "").strip()
        if api_key:
            set_credential(setup.provider_id, api_key)
        result = test_provider(setup)
        state = load_onboarding_state()
        state.update(
            {
                "current_step": "review" if result.get("ok") else "provider",
                "provider_id": setup.provider_id,
                "provider_test_ok": bool(result.get("ok")),
            }
        )
        save_onboarding_state(state)
        return JSONResponse(result)

    @router.post("/onboarding/complete")
    async def complete_onboarding() -> RedirectResponse:
        status = local_readiness_status()
        if not status["ready"]:
            raise HTTPException(status_code=409, detail=status["reasons"])
        state = load_onboarding_state()
        state.update({"current_step": "complete", "complete": True})
        save_onboarding_state(state)
        return RedirectResponse("/admin/runs", status_code=303)

    @router.get("/readiness")
    async def local_readiness() -> JSONResponse:
        return JSONResponse(local_readiness_status())

    @router.post("/folder-picker")
    async def folder_picker() -> JSONResponse:
        if os.name != "nt":
            raise HTTPException(status_code=404, detail="Native folder picker is Windows-only")
        from tkinter import TclError, Tk, filedialog

        try:
            root = Tk()
        except TclError:
            return JSONResponse({"path": None})
        root.withdraw()
        try:
            selected = filedialog.askdirectory()
        finally:
            root.destroy()
        return JSONResponse({"path": selected or None})

    @router.get("/data", response_class=HTMLResponse)
    async def data_and_backup(request: Request):
        return templates.TemplateResponse(
            request=request,
            name="local_data_backup.html",
            context={"storage": inspect_local_storage(_local_paths())},
        )

    @router.post("/data/backup")
    async def create_backup(request: Request) -> FileResponse:
        _require_idle(request)
        paths = _local_paths()
        completed_ids = {
            run.run_id
            for run in request.app.state.run_store.list_runs(limit=500, include_archived=True)
            if str(getattr(run, "status", "")).strip().lower().removeprefix("runstatus.") == "succeeded"
        }
        filename = f"fitcv-backup-{datetime.now(timezone.utc):%Y%m%d-%H%M%S}.fitcv.zip"
        archive = create_backup_archive(
            paths,
            paths.backups_path / filename,
            app_version=str(getattr(request.app.state, "app_version", "0.1.0")),
            completed_run_ids=completed_ids,
        )
        return FileResponse(archive, filename=filename, media_type="application/zip")

    @router.post("/data/relocate", status_code=202)
    async def request_relocation(request: Request) -> JSONResponse:
        _require_idle(request)
        form = await request.form()
        destination = Path(str(form.get("destination") or ""))
        validate_data_root_destination(
            destination,
            source_root=_data_root(),
            source_size_bytes=sum(
                path.stat().st_size for path in _data_root().rglob("*") if path.is_file()
            ),
        )
        write_pending_operation(
            default_pending_operation_path(),
            {"operation": "relocate", "destination": str(destination.resolve())},
        )
        _signal_shutdown(request)
        return JSONResponse(
            {"restart_required": True, "destination": str(destination.resolve())},
            status_code=202,
        )

    @router.post("/data/import", status_code=202)
    async def request_import(request: Request) -> JSONResponse:
        _require_idle(request)
        form = await request.form()
        upload = form.get("archive")
        destination = Path(str(form.get("destination") or ""))
        if upload is None or not hasattr(upload, "read"):
            raise HTTPException(status_code=422, detail="Backup archive is required")
        paths = _local_paths()
        staged_archive = paths.uploads_path / "pending-import.fitcv.zip"
        size = 0
        with staged_archive.open("wb") as handle:
            while chunk := await upload.read(1024 * 1024):
                size += len(chunk)
                if size > MAX_BACKUP_ARCHIVE_BYTES:
                    staged_archive.unlink(missing_ok=True)
                    raise HTTPException(status_code=413, detail="Backup archive exceeds size limit")
                handle.write(chunk)
        try:
            with tempfile.TemporaryDirectory(dir=paths.temporary_path) as raw:
                restore_backup_archive(
                    staged_archive,
                    Path(raw) / "validation",
                    current_db_schema_version=sqlite_schema_version(paths.sqlite_path),
                )
        except (OSError, ValueError, zipfile.BadZipFile) as exc:
            staged_archive.unlink(missing_ok=True)
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        write_pending_operation(
            default_pending_operation_path(),
            {
                "operation": "import",
                "archive": str(staged_archive),
                "destination": str(destination.resolve()),
            },
        )
        _signal_shutdown(request)
        return JSONResponse({"restart_required": True}, status_code=202)

    @router.get("/system", response_class=HTMLResponse)
    async def local_system(request: Request):
        return templates.TemplateResponse(
            request=request,
            name="local_system.html",
            context={"system": _system_metadata(request)},
        )

    @router.get("/system/diagnostics")
    async def diagnostics(request: Request) -> Response:
        paths = _local_paths()
        safe_lines: list[str] = []
        home = str(Path.home())
        for log_path in sorted(paths.logs_path.glob("*.log")):
            try:
                lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()[-200:]
            except OSError:
                continue
            for line in lines:
                if SENSITIVE_LOG_PATTERN.search(line) or not SAFE_LOG_PATTERN.fullmatch(line):
                    continue
                safe_lines.append(
                    re.sub(r"://[^/@\s]+@", "://[redacted]@", line)
                    .replace(home, "%USERPROFILE%")
                    .replace(str(paths.data_root), "%FITCV_DATA_ROOT%")
                )
        output = io.BytesIO()
        with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
            bundle.writestr("system.json", json.dumps(_system_metadata(request), indent=2) + "\n")
            bundle.writestr("log_tail.txt", "\n".join(safe_lines) + ("\n" if safe_lines else ""))
        return Response(
            output.getvalue(),
            media_type="application/zip",
            headers={"Content-Disposition": 'attachment; filename="fitcv-diagnostics.zip"'},
        )

    @router.post("/system/shutdown", response_class=HTMLResponse)
    async def shutdown(request: Request):
        if not bool(getattr(request.app.state, "local_draining", False)):
            _require_idle(request)
            _signal_shutdown(request)
        return templates.TemplateResponse(request=request, name="local_stopped.html", context={})

    return router

def _system_metadata(request: Request) -> dict[str, object]:
    paths = _local_paths()
    setup = _configured_provider_setup()
    storage = inspect_local_storage(paths)
    return {
        "application_version": str(getattr(request.app.state, "app_version", "0.1.0")),
        "build_id": str(getattr(request.app.state, "build_id", "development")),
        "os": platform.platform(),
        "data_path": {"drive": paths.data_root.drive, "name": paths.data_root.name},
        "database_schema_version": storage["database_schema_version"],
        "database_integrity": storage["database_integrity"],
        "provider_host": urlsplit(setup.base_url).hostname if setup is not None else None,
        "wire_api": setup.wire_api if setup is not None else None,
        "models": sorted(set(setup.task_models.values())) if setup is not None else [],
        "readiness": {
            "ready": bool(local_readiness_status()["ready"]),
            "reasons": list(local_readiness_status()["reasons"]),
        },
    }
