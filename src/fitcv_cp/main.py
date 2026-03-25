"""Uvicorn entrypoint for the FitCV admin web service."""
import os

from google.cloud import bigquery

from fitcv_cp.app import create_app

bq = bigquery.Client()
app = create_app(
    bq=bq,
    project=os.environ["GCP_PROJECT"],
    dataset=os.environ.get("BIGQUERY_DATASET", "fitcv"),
    redis_url=os.environ.get("REDIS_URL", "redis://redis:6379/0"),
)
