"""RQ job: execute one pipeline run and persist lifecycle state.

Worker failure path:
1. update run status → failed (with error_message + error_stage)
2. append a pipeline_failed event to the event log
"""
import datetime
import logging
import os
import uuid

from google.cloud import bigquery

from fitcv.pipeline import run_pipeline
from fitcv_cp.bq_store import append_event, update_run_status
from fitcv_cp.models import RunEvent, RunStatus

logger = logging.getLogger(__name__)


def _get_bq() -> bigquery.Client:
    return bigquery.Client()


def execute_pipeline_run(run_id: str, jobs_path: str, config_path: str) -> None:
    project = os.environ.get("GCP_PROJECT", "")
    dataset = os.environ.get("BIGQUERY_DATASET", "fitcv")
    bq = _get_bq()

    # Import here to avoid circular deps at module load time
    from fitcv_cp.reporter import PipelineReporter

    try:
        update_run_status(
            run_id, RunStatus.RUNNING, bq, project=project, dataset=dataset,
            started_at=datetime.datetime.now(datetime.timezone.utc),
        )
        reporter = PipelineReporter(run_id=run_id, bq=bq, project=project, dataset=dataset)
        summary = run_pipeline(jobs_path=jobs_path, config_path=config_path, reporter=reporter)
        # run_pipeline() contract: returns {total_jobs, passed_filter, ranked, cvs_generated}
        update_run_status(
            run_id, RunStatus.SUCCEEDED, bq, project=project, dataset=dataset,
            finished_at=datetime.datetime.now(datetime.timezone.utc), summary=summary,
        )
    except Exception as exc:
        logger.error("[run_id=%s] Pipeline failed: %s", run_id, exc)
        # 1. Update run row
        update_run_status(
            run_id, RunStatus.FAILED, bq, project=project, dataset=dataset,
            finished_at=datetime.datetime.now(datetime.timezone.utc), error_message=str(exc),
        )
        # 2. Append error event so the UI timeline shows the failure
        try:
            append_event(
                RunEvent(
                    run_id=run_id,
                    event_id=str(uuid.uuid4()),
                    stage="pipeline_failed",
                    level="error",
                    message=str(exc),
                    created_at=datetime.datetime.now(datetime.timezone.utc),
                ),
                bq,
                project=project,
                dataset=dataset,
            )
        except Exception as inner:
            logger.warning("[run_id=%s] Failed to write failure event: %s", run_id, inner)
