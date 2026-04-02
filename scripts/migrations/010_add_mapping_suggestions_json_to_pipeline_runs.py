"""Add mapping_suggestions_json to pipeline_runs.

Run with:
    python scripts/migrations/010_add_mapping_suggestions_json_to_pipeline_runs.py
"""

from __future__ import annotations

import os

from google.cloud import bigquery

from fitcv.config import load_config


def main() -> None:
    config = load_config()
    project = str(config["gcp_project"])
    dataset = str(config["bigquery_dataset"])
    client = bigquery.Client(project=project)
    table = f"{project}.{dataset}.pipeline_runs"
    sql = f"""
    ALTER TABLE `{table}`
    ADD COLUMN IF NOT EXISTS mapping_suggestions_json STRING
    OPTIONS(description="Immutable run-scoped mapping suggestions snapshot")
    """
    client.query(sql).result()
    print(f"Updated {table}")


if __name__ == "__main__":
    os.environ.setdefault("GOOGLE_APPLICATION_CREDENTIALS", str(load_config()["service_account_key"]))
    main()
