"""Uvicorn entrypoint for the FitCV admin web service."""

import logging
import os
import warnings
from pathlib import Path
from typing import Any

from fitcv.config import load_control_plane_config
from fitcv_cp.app import create_app
from fitcv_cp.bq_store import get_pipeline_runs_schema_status

logger = logging.getLogger(__name__)


def _validate_google_credentials_path() -> None:
    """Resolve credentials path when possible; otherwise fall back to ADC."""
    credentials_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if not credentials_path:
        return

    path = Path(credentials_path)
    if not path.exists():
        warnings.warn(
            "GOOGLE_APPLICATION_CREDENTIALS does not exist: "
            f"{credentials_path}. Falling back to ADC.",
            RuntimeWarning,
            stacklevel=2,
        )
        os.environ.pop("GOOGLE_APPLICATION_CREDENTIALS", None)
        return
    if path.is_dir():
        candidates = sorted(candidate for candidate in path.glob("*.json") if candidate.is_file())
        if len(candidates) == 1:
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(candidates[0])
            return
        warnings.warn(
            "GOOGLE_APPLICATION_CREDENTIALS points to a directory without a single "
            f"key JSON file: {credentials_path}. Falling back to ADC.",
            RuntimeWarning,
            stacklevel=2,
        )
        os.environ.pop("GOOGLE_APPLICATION_CREDENTIALS", None)


def _resolve_backend_type() -> str:
    cfg = load_control_plane_config()
    backend_type = str(((cfg.get("data_backend") or {}).get("type") or "bigquery")).strip().lower()
    if backend_type not in {"bigquery", "sqlite"}:
        raise ValueError(f"Unsupported backend type: {backend_type}")
    return backend_type


def _resolve_project_dataset() -> tuple[str, str]:
    cfg = load_control_plane_config()
    bq_cfg = dict(((cfg.get("data_backend") or {}).get("bigquery") or {}))
    project = str(os.environ.get("GCP_PROJECT") or bq_cfg.get("project") or "").strip()
    dataset = str(os.environ.get("BIGQUERY_DATASET") or bq_cfg.get("dataset") or "fitcv").strip() or "fitcv"
    return project, dataset


def _build_bigquery_client() -> Any:
    _validate_google_credentials_path()
    from google.cloud import bigquery

    return bigquery.Client()


def build_app() -> Any:
    backend_type = _resolve_backend_type()
    project, dataset = _resolve_project_dataset()
    redis_url = os.environ.get("REDIS_URL", "redis://redis:6379/0")

    if backend_type == "sqlite":
        logger.info("control-plane backend mode: sqlite")
        return create_app(
            bq=None,
            project=project or "local",
            dataset=dataset,
            redis_url=redis_url,
        )

    if not project:
        raise ValueError("GCP_PROJECT must be set for bigquery backend mode")

    bq = _build_bigquery_client()
    schema_status = get_pipeline_runs_schema_status(
        bq,
        project=project,
        dataset=dataset,
    )
    if schema_status.get("status") == "complete":
        logger.info(
            "orchestration schema mode: complete (%s.%s.pipeline_runs)",
            project,
            dataset,
        )
    elif schema_status.get("status") == "fallback":
        missing = ", ".join(schema_status.get("missing_columns") or [])
        logger.warning(
            "orchestration schema mode: fallback (missing columns: %s). "
            "Run migration to add orchestration_backend and orchestration_run_id.",
            missing or "unknown",
        )
    else:
        logger.warning(
            "orchestration schema mode: unknown (%s).",
            schema_status.get("warning") or "schema check failed",
        )

    return create_app(
        bq=bq,
        project=project,
        dataset=dataset,
        redis_url=redis_url,
    )


app = build_app()
