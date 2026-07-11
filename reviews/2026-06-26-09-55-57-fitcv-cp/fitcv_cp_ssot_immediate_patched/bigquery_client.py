"""Canonical BigQuery client construction for all control-plane processes."""

from __future__ import annotations

import logging
import os
import warnings
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def validate_google_credentials_path() -> None:
    """Resolve a credentials file when possible; otherwise fall back to ADC."""
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


def build_bigquery_client() -> Any:
    """Build the canonical BigQuery client used by web, worker, and reconciler."""
    validate_google_credentials_path()
    from google.cloud import bigquery

    return bigquery.Client()
