"""Ingest raw LinkedIn job postings JSON into BigQuery.

Public API
----------
parse_jobs_file       : load raw JSON array from disk
validate_linkedin_schema : check required scraper fields exist
snake_case_keys       : convert camelCase scraper keys to snake_case
prepare_raw_rows      : map raw jobs into the raw_jobs BQ schema
load_to_bigquery      : insert rows into fitcv.raw_jobs (requires credentials)
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ── field mapping: LinkedIn scraper camelCase → raw_jobs snake_case ──────────

_CAMEL_TO_SNAKE: dict[str, str] = {
    "jobUrl": "job_url",
    "postedTime": "posted_time",
    "publishedAt": "published_at",
    "companyName": "company_name",
    "companyUrl": "company_url",
    "companyId": "company_id",
    "applicationsCount": "applications_count",
    "contractType": "contract_type",
    "experienceLevel": "experience_level",
    "workType": "work_type",
    "posterFullName": "poster_full_name",
    "posterProfileUrl": "poster_profile_url",
    "applyUrl": "apply_url",
    "applyType": "apply_type",
}

# Fields the scraper must always provide
_REQUIRED_SCRAPER_FIELDS: list[str] = [
    "jobUrl",
    "title",
    "companyName",
    "description",
    "contractType",
    "experienceLevel",
]


# ── parsing ──────────────────────────────────────────────────────────────────

def parse_jobs_file(path: str | Path) -> list[dict[str, Any]]:
    """Load a JSON array of LinkedIn job objects from *path*.

    Raises:
        FileNotFoundError: if the file does not exist.
        ValueError: if the file does not contain a JSON array.
    """
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"Jobs file not found: {file_path}")

    with open(file_path, encoding="utf-8") as f:
        data: Any = json.load(f)

    if not isinstance(data, list):
        raise ValueError(f"Jobs file must contain a JSON array, expected a JSON array but got {type(data).__name__}")

    return data  # type: ignore[return-value]


def validate_linkedin_schema(job: dict[str, Any]) -> list[str]:
    """Return a list of error strings for any missing required scraper fields.

    Returns an empty list when the job is valid.
    """
    return [
        f"Missing required field: '{field}'"
        for field in _REQUIRED_SCRAPER_FIELDS
        if field not in job
    ]


# ── key conversion ────────────────────────────────────────────────────────────

def snake_case_keys(job: dict[str, Any]) -> dict[str, Any]:
    """Return a new dict with camelCase LinkedIn keys mapped to snake_case.

    Fields not in the mapping are preserved as-is with their original key.
    """
    return {_CAMEL_TO_SNAKE.get(k, k): v for k, v in job.items()}


# ── row preparation ───────────────────────────────────────────────────────────

def prepare_raw_rows(jobs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Map a list of LinkedIn scraper dicts into raw_jobs BQ schema rows.

    Each row includes the full original JSON in `raw_json` for auditability
    and an `ingested_at` timestamp set to the current UTC time.
    """
    ingested_at = datetime.now(tz=timezone.utc).isoformat()

    rows: list[dict[str, Any]] = []
    for job in jobs:
        snaked = snake_case_keys(job)
        row: dict[str, Any] = {
            "job_url":            snaked.get("job_url", ""),
            "title":              snaked.get("title", ""),
            "location":           snaked.get("location", ""),
            "posted_time":        snaked.get("posted_time", ""),
            "published_at":       snaked.get("published_at", None),
            "company_name":       snaked.get("company_name", ""),
            "company_url":        snaked.get("company_url", ""),
            "company_id":         snaked.get("company_id", ""),
            "description":        snaked.get("description", ""),
            "applications_count": snaked.get("applications_count", ""),
            "contract_type":      snaked.get("contract_type", ""),
            "experience_level":   snaked.get("experience_level", ""),
            "work_type":          snaked.get("work_type", ""),
            "sector":             snaked.get("sector", ""),
            "salary":             snaked.get("salary", ""),
            "apply_url":          snaked.get("apply_url", ""),
            "apply_type":         snaked.get("apply_type", ""),
            "raw_json":           json.dumps(job, ensure_ascii=False),
            "ingested_at":        ingested_at,
        }
        rows.append(row)

    return rows


# ── BigQuery load (integration) ───────────────────────────────────────────────

def load_to_bigquery(rows: list[dict[str, Any]], config: dict[str, Any]) -> int:
    """Insert *rows* into fitcv.raw_jobs and return the number of rows inserted.

    Requires GOOGLE_APPLICATION_CREDENTIALS to be set.
    Decorated with @pytest.mark.integration in tests.

    Args:
        rows:   Output of prepare_raw_rows().
        config: Dict from load_config() containing gcp_project, bigquery_dataset,
                and service_account_key.

    Returns:
        Number of rows successfully inserted.
    """
    from google.cloud import bigquery  # type: ignore[import-untyped]
    from google.oauth2 import service_account  # type: ignore[import-untyped]

    key_path: str = str(config["service_account_key"])
    project: str = str(config["gcp_project"])
    dataset: str = str(config["bigquery_dataset"])

    credentials = service_account.Credentials.from_service_account_file(key_path)
    client = bigquery.Client(project=project, credentials=credentials)

    table_ref = f"{project}.{dataset}.raw_jobs"
    errors = client.insert_rows_json(table_ref, rows)

    if errors:
        raise RuntimeError(f"BigQuery insert errors: {errors}")

    return len(rows)
