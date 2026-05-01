"""Uvicorn entrypoint for the FitCV admin web service."""
import os
import warnings
from pathlib import Path

from google.cloud import bigquery

from fitcv_cp.app import create_app


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
app = create_app(
    bq=bq,
    project=os.environ["GCP_PROJECT"],
    dataset=os.environ.get("BIGQUERY_DATASET", "fitcv"),
    redis_url=os.environ.get("REDIS_URL", "redis://redis:6379/0"),
)
