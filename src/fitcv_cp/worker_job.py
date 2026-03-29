"""RQ job: execute one pipeline run and persist lifecycle state.

Worker lifecycle order:
1. update run status → running
2. read current run row (check cancel_requested_at)
3. if already cancelled: mark cancelled, append run_cancelled, exit early
4. otherwise: run pipeline with cancellation_check callback
5. on PipelineCancelled: mark cancelled, append run_cancelled
6. on success: mark succeeded
7. on unexpected exception: mark failed, append pipeline_failed event
"""
import datetime
import json
import logging
import os
import uuid
from typing import Any

from google.cloud import bigquery

from fitcv.pipeline import PipelineCancelled, run_pipeline
from fitcv_cp.bq_store import append_event, get_run, update_run_results_export, update_run_status
from fitcv_cp.models import RunEvent, RunStatus

logger = logging.getLogger(__name__)


def _get_bq() -> bigquery.Client:
    return bigquery.Client()


def _run_cancelled_event(run_id: str, message: str) -> RunEvent:
    return RunEvent(
        run_id=run_id,
        event_id=str(uuid.uuid4()),
        stage="run_cancelled",
        level="warning",
        message=message,
        created_at=datetime.datetime.now(datetime.timezone.utc),
    )


def _build_results_export_payload(
    *,
    run_id: str,
    run_record: Any,
    summary: dict[str, Any],
    export_results: list[dict[str, Any]],
    finished_at: datetime.datetime,
) -> str:
    def _json_safe(value: Any) -> Any:
        if isinstance(value, datetime.datetime):
            return value.isoformat()
        if isinstance(value, datetime.date):
            return value.isoformat()
        if isinstance(value, dict):
            return {str(k): _json_safe(v) for k, v in value.items()}
        if isinstance(value, list):
            return [_json_safe(item) for item in value]
        if isinstance(value, tuple):
            return [_json_safe(item) for item in value]
        if isinstance(value, set):
            return [_json_safe(item) for item in sorted(value)]
        return value

    def _string_or_none(value: Any) -> str | None:
        return value if isinstance(value, str) else None

    def _iso_or_none(value: Any) -> str | None:
        return value.isoformat() if isinstance(value, datetime.datetime) else None

    payload = {
        "run_id": run_id,
        "status": RunStatus.SUCCEEDED.value,
        "triggered_by": _string_or_none(getattr(run_record, "triggered_by", "")) or "",
        "created_at": _iso_or_none(getattr(run_record, "created_at", None)),
        "started_at": _iso_or_none(getattr(run_record, "started_at", None)),
        "finished_at": finished_at.isoformat(),
        "jobs_path": _string_or_none(getattr(run_record, "jobs_path", "")) or "",
        "jobs_input_source": _string_or_none(getattr(run_record, "jobs_input_source", None)),
        "candidate_profile_source": _string_or_none(getattr(run_record, "candidate_profile_source", None)),
        "summary": {
            "total_jobs": int(summary.get("total_jobs", 0)),
            "passed_filter": int(summary.get("passed_filter", 0)),
            "ranked": int(summary.get("ranked", 0)),
            "cvs_generated": int(summary.get("cvs_generated", 0)),
        },
        "results": _json_safe(export_results),
    }
    return json.dumps(payload, ensure_ascii=False)


def execute_pipeline_run(run_id: str, jobs_path: str, config_path: str) -> None:
    project = os.environ.get("GCP_PROJECT", "")
    dataset = os.environ.get("BIGQUERY_DATASET", "fitcv")
    bq = _get_bq()

    # Fall back to config file if GCP_PROJECT env var is not set — the worker
    # may be started without env vars even though the config file is always present.
    if not project:
        try:
            from fitcv.config import load_config as _load_config
            _cfg = _load_config(config_path)
            project = str(_cfg.get("gcp_project", ""))
            dataset = str(_cfg.get("bigquery_dataset", dataset))
        except Exception as exc:
            logger.warning("Could not load config for project/dataset fallback: %s", exc)

    # Import here to avoid circular deps at module load time
    from fitcv_cp.reporter import PipelineReporter

    try:
        # ── Step 1: Mark running ──────────────────────────────────────────────
        update_run_status(
            run_id, RunStatus.RUNNING, bq, project=project, dataset=dataset,
            started_at=datetime.datetime.now(datetime.timezone.utc),
        )

        # ── Step 2: Read current row (reads cancel_requested_at + config snapshot)
        run_record = get_run(run_id, bq, project=project, dataset=dataset)
        effective_config: dict | None = None
        if run_record and run_record.effective_settings_json:
            try:
                effective_config = json.loads(run_record.effective_settings_json)
            except Exception as exc:
                logger.warning("[run_id=%s] Failed to parse effective_settings_json: %s", run_id, exc)

        # ── Step 3: Early-exit if cancellation already requested ──────────────
        if run_record and run_record.cancel_requested_at is not None:
            logger.info("[run_id=%s] Cancellation already requested — exiting early", run_id)
            update_run_status(
                run_id, RunStatus.CANCELLED, bq, project=project, dataset=dataset,
                finished_at=datetime.datetime.now(datetime.timezone.utc),
            )
            append_event(
                _run_cancelled_event(run_id, "Run cancelled before pipeline execution started"),
                bq, project=project, dataset=dataset,
            )
            return

        # ── Step 4: Run pipeline with cooperative cancellation check ──────────
        reporter = PipelineReporter(run_id=run_id, bq=bq, project=project, dataset=dataset)

        def _cancellation_check() -> bool:
            """Lightweight re-read to check if cancel was requested mid-flight."""
            current = get_run(run_id, bq, project=project, dataset=dataset)
            return current is not None and current.cancel_requested_at is not None

        summary = run_pipeline(
            jobs_path=jobs_path,
            config_path=config_path,
            reporter=reporter,
            config=effective_config,
            run_id=run_id,
            cancellation_check=_cancellation_check,
        )

        # ── Step 5: Success ───────────────────────────────────────────────────
        finished_at = datetime.datetime.now(datetime.timezone.utc)
        update_run_status(
            run_id, RunStatus.SUCCEEDED, bq, project=project, dataset=dataset,
            finished_at=finished_at, summary=summary,
        )
        export_results = list(summary.get("export_results") or [])
        try:
            update_run_results_export(
                run_id,
                _build_results_export_payload(
                    run_id=run_id,
                    run_record=run_record,
                    summary=summary,
                    export_results=export_results,
                    finished_at=finished_at,
                ),
                bq,
                project=project,
                dataset=dataset,
            )
        except Exception as exc:
            logger.warning("[run_id=%s] Failed to persist results export snapshot: %s", run_id, exc)

    except PipelineCancelled as exc:
        # ── Step 5 (alt): Pipeline was cancelled at a checkpoint ──────────────
        logger.info("[run_id=%s] Pipeline cancelled at checkpoint: %s", run_id, exc)
        update_run_status(
            run_id, RunStatus.CANCELLED, bq, project=project, dataset=dataset,
            finished_at=datetime.datetime.now(datetime.timezone.utc),
        )
        try:
            append_event(
                _run_cancelled_event(run_id, f"Run cancelled at pipeline checkpoint: {exc}"),
                bq, project=project, dataset=dataset,
            )
        except Exception as inner:
            logger.warning("[run_id=%s] Failed to write cancellation event: %s", run_id, inner)

    except Exception as exc:
        # ── Step 7: Unexpected pipeline failure ───────────────────────────────
        logger.error("[run_id=%s] Pipeline failed: %s", run_id, exc)
        update_run_status(
            run_id, RunStatus.FAILED, bq, project=project, dataset=dataset,
            finished_at=datetime.datetime.now(datetime.timezone.utc), error_message=str(exc),
        )
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
