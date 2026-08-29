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
from fitcv.config import (
    PROMPT_ADDENDUM_TASK_IDS,
    PROVIDER_REGISTRY,
    SUPPORTED_AUTH_MODES,
    SUPPORTED_ROUTING_PARTS,
    SUPPORTED_WIRE_APIS,
    load_control_plane_config,
    load_local_controller_overlay,
    load_prompt_task_registry,
    resolve_model_routing_part,
)
from fitcv_cp.local_credentials import credential_is_configured, get_credential, set_credential
from fitcv_cp import provider_registry
from fitcv_cp.local_setup import (
    TASK_PARTS,
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
    local_storage_paths,
    restore_backup_archive,
    sqlite_schema_version,
    validate_data_root_destination,
    write_pending_operation,
)
from fitcv_cp.settings_store import load_llm_configuration
from fitcv_cp.store import ControlPlaneStore


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
    *TASK_PARTS,
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
    return local_storage_paths(
        Path(os.environ["APPDATA"]) / "FitCV" / "bootstrap.json",
        _data_root(),
    )

def local_data_status_resource(request: Request) -> dict[str, Any]:
    reasons = active_work_reasons(request)
    return {
        "storage": inspect_local_storage(_local_paths()),
        "active_work_reasons": reasons,
        "capabilities": {"can_backup": not reasons, "can_import": not reasons},
    }

def local_lifecycle_status_resource(request: Request) -> dict[str, Any]:
    reasons = active_work_reasons(request)
    return {
        "system": _system_metadata(request),
        "active_work_reasons": reasons,
        "capabilities": {
            "can_relocate": not reasons,
            "can_shutdown": not reasons,
            "folder_picker": os.name == "nt",
            "diagnostics": True,
        },
    }

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
    payload = {
        key: payload[key]
        for key in ("version", "current_step", "complete", "provider_test_ok", "provider_id", "drafts", "errors")
        if key in payload
    }
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
    control_plane = load_control_plane_config()
    provider_id = str(form.get("provider_id") or "openai_compatible").strip().lower()
    provider_defaults = dict((control_plane.get("providers") or {}).get(provider_id) or {})
    if not provider_defaults:
        raise ValueError(f"unsupported provider_id: {provider_id}")
    routes = {
        part: resolve_model_routing_part(part)
        for part in SUPPORTED_ROUTING_PARTS
    }
    default_model = str(
        form.get("default_model")
        or routes["cv_generation_structured_write"]["model"]
    ).strip()
    retry: dict[str, Any] = {}
    prompt_addenda: dict[str, str] = {}
    if str(form.get("controller_settings_present") or "") == "1":
        retry_defaults = dict((control_plane.get("fitcv_cp") or {}).get("retry") or {})
        raw_backoff = str(
            form.get("retry_backoff_seconds")
            or ",".join(str(value) for value in retry_defaults["backoff_seconds"])
        )
        try:
            backoff_seconds = [int(value.strip()) for value in raw_backoff.split(",") if value.strip()]
        except ValueError as exc:
            raise ValueError("Run retry backoff must be comma-separated integers") from exc
        retry = {
            "enabled": form.get("retry_enabled") is not None,
            "max_attempts": int(
                form.get("retry_max_attempts") or retry_defaults["max_attempts"]
            ),
            "backoff_seconds": backoff_seconds,
            "lease_seconds": int(
                form.get("retry_lease_seconds") or retry_defaults["lease_seconds"]
            ),
            "reconciler_interval_seconds": int(
                form.get("retry_reconciler_interval_seconds")
                or retry_defaults["reconciler_interval_seconds"]
            ),
            "error_details_max_chars": int(
                form.get("retry_error_details_max_chars")
                or retry_defaults["error_details_max_chars"]
            ),
        }
        prompt_addenda = {
            task_id: str(form.get(f"prompt_addendum_{task_id}") or "")
            for task_id in PROMPT_ADDENDUM_TASK_IDS
        }
    provider_meta = PROVIDER_REGISTRY[provider_id]
    return ProviderSetup(
        provider_id=provider_id,
        provider_type=str(provider_meta["type"]),  # type: ignore[arg-type]
        display_name=str(provider_meta["label"]),
        base_url=str(form.get("base_url") or provider_defaults["base_url"]).strip(),
        auth_mode=str(
            form.get("auth_mode") or provider_defaults["auth_mode"]
        ).strip().lower(),  # type: ignore[arg-type]
        wire_api=str(
            form.get("wire_api") or provider_defaults["wire_api"]
        ).strip().lower(),  # type: ignore[arg-type]
        timeout_seconds=float(
            form.get("timeout_seconds") or provider_defaults["timeout_seconds"]
        ),
        default_model=default_model,
        task_models={
            part: str(form.get(part) or routes[part]["model"]).strip()
            for part in SUPPORTED_ROUTING_PARTS
        },
        run_retry=retry,
        prompt_addenda=prompt_addenda,
    )


def _provider_draft(form: Any) -> dict[str, str]:
    return {field: str(form.get(field) or "").strip() for field in PROVIDER_DRAFT_FIELDS}

def _configured_provider_setup() -> ProviderSetup | None:
    state = load_onboarding_state()
    provider_id = str(state.get("provider_id") or "openai_compatible")
    control_plane = load_control_plane_config()
    provider = dict((control_plane.get("providers") or {}).get(provider_id) or {})
    if not provider:
        return None
    parts = dict((control_plane.get("model_routing") or {}).get("parts") or {})
    provider_meta = PROVIDER_REGISTRY[provider_id]
    default_model = str(
        (parts.get("cv_generation_structured_write") or {}).get("model") or ""
    )
    return ProviderSetup(
        provider_id=provider_id,
        provider_type=str(provider_meta["type"]),  # type: ignore[arg-type]
        display_name=str(provider_meta["label"]),
        base_url=str(provider["base_url"]),
        auth_mode=str(provider["auth_mode"]),  # type: ignore[arg-type]
        wire_api=str(provider["wire_api"]),  # type: ignore[arg-type]
        timeout_seconds=float(provider["timeout_seconds"]),
        default_model=default_model,
        task_models={
            part: str((parts.get(part) or {}).get("model") or "")
            for part in SUPPORTED_ROUTING_PARTS
        },
    )


def _controller_view(state: dict[str, Any]) -> dict[str, Any]:
    effective = load_control_plane_config()
    overlay = load_local_controller_overlay()
    parts = dict((effective.get("model_routing") or {}).get("parts") or {})
    active_provider_id = str(
        state.get("provider_id")
        or (parts.get("enrich_extraction") or {}).get("provider")
        or "openai_compatible"
    )
    providers = dict(effective.get("providers") or {})
    provider = dict(providers[active_provider_id])
    overlay_providers = dict(overlay.get("providers") or {})
    overlay_parts = dict((overlay.get("model_routing") or {}).get("parts") or {})
    retry = dict((effective.get("fitcv_cp") or {}).get("retry") or {})
    overlay_retry = dict((overlay.get("fitcv_cp") or {}).get("retry") or {})
    addenda = dict((effective.get("prompts") or {}).get("additional_instructions") or {})
    overlay_addenda = dict((overlay.get("prompts") or {}).get("additional_instructions") or {})
    prompt_registry = load_prompt_task_registry()
    return {
        "provider_id": active_provider_id,
        "providers": [
            {
                "id": provider_id,
                "label": str(meta["label"]),
                "selected": provider_id == active_provider_id,
            }
            for provider_id, meta in PROVIDER_REGISTRY.items()
        ],
        "provider": provider,
        "provider_source": (
            "local" if active_provider_id in overlay_providers else "packaged"
        ),
        "auth_modes": sorted(SUPPORTED_AUTH_MODES),
        "wire_apis": sorted(SUPPORTED_WIRE_APIS),
        "routes": [
            {
                "id": task_id,
                "label": task_id.replace("_", " ").title(),
                "model": str((parts.get(task_id) or {}).get("model") or ""),
                "source": "local" if task_id in overlay_parts else "packaged",
            }
            for task_id in SUPPORTED_ROUTING_PARTS
        ],
        "retry": retry,
        "retry_source": "local" if overlay_retry else "packaged",
        "retry_backoff": ", ".join(str(value) for value in retry["backoff_seconds"]),
        "prompts": [
            {
                "task_id": task_id,
                "label": task_id.replace("_", " ").title(),
                "prompt_id": prompt_registry[task_id]["prompt_id"],
                "version": prompt_registry[task_id]["version"],
                "addendum": str(addenda.get(task_id) or ""),
                "source": "local" if task_id in overlay_addenda else "packaged",
            }
            for task_id in PROMPT_ADDENDUM_TASK_IDS
        ],
    }


def local_readiness_status() -> dict[str, object]:
    reasons: list[str] = []
    try:
        load_onboarding_state()
        store = ControlPlaneStore()
        has_active_profile = bool(store.list_candidate_profiles())
    except RuntimeError:
        return {
            "ready": False,
            "reasons": ["Local readiness could not be verified."],
            "error": {
                "code": "local_readiness_unavailable",
                "retryable": True,
                "action": "Repair local state, then reload readiness.",
            },
        }
    if not store.integration_migration_applied("packaged_local_complete_integration_v1"):
        reasons.append("Local integration migration is incomplete")
    if not has_active_profile:
        reasons.append("Candidate profile is not configured")
    eligible_refs = {
        model["model_record_id"]
        for model in provider_registry.list_eligible_models(store=store)
    }
    default_model_ref = load_llm_configuration().get("default_model_ref")
    if not eligible_refs:
        reasons.append("No verified provider model is available")
    if not default_model_ref:
        reasons.append("Default Route is not configured")
    elif default_model_ref not in eligible_refs:
        reasons.append("Default Route model requires connection or model retest")
    return {"ready": not reasons, "reasons": reasons}


def build_local_router(templates: Jinja2Templates) -> APIRouter:
    router = APIRouter(prefix="/local")

    @router.get("/onboarding")
    async def onboarding(request: Request):
        state = load_onboarding_state()
        if state.get("complete"):
            return RedirectResponse("/admin/runs", status_code=303)
        profile_path = Path(os.environ["FITCV_LOCAL_CANDIDATE_PROFILE_PATH"])
        profile_draft = str((state.get("drafts") or {}).get("profile") or "")
        if not profile_draft and profile_path.exists():
            profile_draft = profile_path.read_text(encoding="utf-8")
        return templates.TemplateResponse(
            request=request,
            name="local_onboarding.html",
            context={
                "state": state,
                "data_root": str(_data_root()),
                "profile_draft": profile_draft,
                "readiness": local_readiness_status(),
            },
            headers={"Cache-Control": "no-store"},
        )

    @router.post("/onboarding/profile")
    async def save_profile(request: Request):
        form = await request.form()
        raw_profile = str(form.get("profile") or "")
        try:
            profile = load_profile_text(raw_profile)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        profile_path = Path(os.environ["FITCV_LOCAL_CANDIDATE_PROFILE_PATH"])
        _write_profile(profile_path, profile)
        state = load_onboarding_state()
        drafts = dict(state.get("drafts") or {})
        drafts["profile"] = raw_profile
        state.update({"current_step": "provider", "drafts": drafts})
        save_onboarding_state(state)
        return RedirectResponse("/local/onboarding", status_code=303)

    @router.post("/onboarding/provider")
    async def save_provider() -> None:
        raise HTTPException(
            status_code=410,
            detail="Use the canonical API Providers resource.",
        )

    @router.post("/onboarding/models/discover")
    async def discover_provider_models() -> None:
        raise HTTPException(
            status_code=410,
            detail="Use the canonical provider model resource.",
        )

    @router.post("/onboarding/provider/test")
    async def run_provider_test() -> None:
        raise HTTPException(
            status_code=410,
            detail="Use the canonical provider connection test resource.",
        )

    @router.post("/onboarding/controller/reset")
    async def reset_controller_override() -> None:
        raise HTTPException(
            status_code=410,
            detail="Legacy controller overrides are retired.",
        )

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
        status = local_readiness_status()
        return JSONResponse(status_code=503 if status.get("error") else 200, content=status)

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
            context={"data_status": local_data_status_resource(request)},
        )

    @router.get("/data/status")
    async def data_status(request: Request) -> JSONResponse:
        return JSONResponse(local_data_status_resource(request))

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
        return RedirectResponse("/admin/lifecycle", status_code=302)

    @router.get("/lifecycle/status")
    async def lifecycle_status(request: Request) -> JSONResponse:
        return JSONResponse(local_lifecycle_status_resource(request))

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
    storage = inspect_local_storage(paths)
    store = getattr(request.app.state, "run_store", None) or ControlPlaneStore()
    providers = provider_registry.list_providers(store=store)
    eligible_models = provider_registry.list_eligible_models(store=store)
    return {
        "application_version": str(getattr(request.app.state, "app_version", "0.1.0")),
        "build_id": str(getattr(request.app.state, "build_id", "development")),
        "os": platform.platform(),
        "data_path": {"drive": paths.data_root.drive, "name": paths.data_root.name},
        "database_schema_version": storage["database_schema_version"],
        "database_integrity": storage["database_integrity"],
        "provider_hosts": sorted(
            {
                urlsplit(str(provider.get("base_url") or "")).hostname
                for provider in providers
                if provider.get("connection_status") == "verified" and provider.get("base_url")
            }
            - {None}
        ),
        "eligible_model_count": len(eligible_models),
        "readiness": {
            "ready": bool(local_readiness_status()["ready"]),
            "reasons": list(local_readiness_status()["reasons"]),
        },
    }
