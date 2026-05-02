"""Uvicorn entrypoint for the FitCV admin web service."""
import logging
import os
import warnings
from pathlib import Path

from google.cloud import bigquery

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
        return


_validate_google_credentials_path()
bq = bigquery.Client()
_project = os.environ["GCP_PROJECT"]
_dataset = os.environ.get("BIGQUERY_DATASET", "fitcv")
_schema_status = get_pipeline_runs_schema_status(
    bq,
    project=_project,
    dataset=_dataset,
)
if _schema_status.get("status") == "complete":
    logger.info(
        "orchestration schema mode: complete (%s.%s.pipeline_runs)",
        _project,
        _dataset,
    )
elif _schema_status.get("status") == "fallback":
    missing = ", ".join(_schema_status.get("missing_columns") or [])
    logger.warning(
        "orchestration schema mode: fallback (missing columns: %s). "
        "Run migration to add orchestration_backend and orchestration_run_id.",
        missing or "unknown",
    )
else:
    logger.warning(
        "orchestration schema mode: unknown (%s).",
        _schema_status.get("warning") or "schema check failed",
    )
app = create_app(
    bq=bq,
    project=_project,
    dataset=_dataset,
    redis_url=os.environ.get("REDIS_URL", "redis://redis:6379/0"),
)
